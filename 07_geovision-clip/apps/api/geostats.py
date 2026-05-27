"""
geostats.py - Nucleo geoestadistico de GeoVision-CLIP Cali.

Funciones puras (sin estado, sin I/O) para:
  - forecast temporal por persistencia con incertidumbre por horizonte,
  - Kriging Ordinario espacial sobre las estaciones DAGMA (PyKrige) con fallback IDW,
  - validacion Leave-One-Station-Out (LOO-CV),
  - Indice de Moran global sobre la superficie predicha.

Unidades: todo en microgramos por metro cubico (ug/m3), concentracion de superficie.
Las predicciones del modelo profundo v11 (columna troposferica, mol/m2) NO entran aqui
como valor; se usan aparte solo como patron espacial relativo (capa overlay).
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass

import numpy as np

# SEED del proyecto (prohibido 42). El mock previo uso 137; se mantiene por coherencia.
SEED = 137


# ---------------------------------------------------------------------------
# Forecast temporal por persistencia
# ---------------------------------------------------------------------------

@dataclass
class Forecast:
    """Pronostico de una estacion para un horizonte: valor central y sigma temporal."""
    valor: float
    sigma: float
    n: int


def _acf_lag1(serie: np.ndarray) -> float:
    """Autocorrelacion de lag 1 (coeficiente AR(1) empirico) en [0, 1)."""
    serie = serie[np.isfinite(serie)]
    if serie.size < 10:
        return 0.0
    a = serie[:-1] - serie[:-1].mean()
    b = serie[1:] - serie[1:].mean()
    denom = np.sqrt(np.sum(a ** 2) * np.sum(b ** 2))
    return float(np.sum(a * b) / denom) if denom > 1e-12 else 0.0


def forecast_reversion(serie: np.ndarray, horizonte_dias: int,
                       ventana: int = 30) -> Forecast:
    """
    Pronostico por reversion a la media (AR(1)) para horizonte corto.

    Persistencia pura (repetir el ultimo valor) da el mismo pronostico para T+1, T+3
    y T+7, lo que vuelve identicos los mapas de los tres horizontes. La reversion a la
    media corrige eso de forma fisicamente justificada: un contaminante ambiental
    regresa hacia su nivel climatologico a medida que crece el horizonte. El estimador
    AR(1) optimo es

        E[x(t+h) | reciente] = mu + phi**h * (x_reciente - mu)

    donde mu es la climatologia (mediana de toda la serie), x_reciente es la mediana de
    la ventana reciente (robusta a outliers) y phi es la autocorrelacion de lag 1. A T+1
    el pronostico queda cerca de lo observado; a T+7 regresa hacia mu.

    La incertidumbre sigma es el RMSE de persistencia a `horizonte_dias` (error tipico de
    usar y(t-h) como prediccion de y(t)): crece con el horizonte de forma empirica y es
    una cota conservadora del error del pronostico.

    serie : valores diarios ordenados cronologicamente (puede traer NaN; se filtran).
    """
    serie = np.asarray(serie, dtype=float)
    serie = serie[np.isfinite(serie)]
    if serie.size == 0:
        return Forecast(valor=float("nan"), sigma=float("nan"), n=0)

    reciente = serie[-ventana:] if serie.size >= ventana else serie
    x_reciente = float(np.median(reciente))
    mu = float(np.median(serie))
    phi = float(np.clip(_acf_lag1(serie), 0.0, 0.98))
    valor = mu + phi ** horizonte_dias * (x_reciente - mu)

    if serie.size > horizonte_dias:
        diff = serie[horizonte_dias:] - serie[:-horizonte_dias]
        sigma = float(np.sqrt(np.mean(diff ** 2)))
    else:
        sigma = float(np.std(reciente)) if reciente.size > 1 else 0.0

    return Forecast(valor=float(valor), sigma=max(sigma, 1e-6), n=int(serie.size))


# ---------------------------------------------------------------------------
# Interpolacion espacial: Kriging Ordinario con fallback IDW
# ---------------------------------------------------------------------------

def _idw(lons: np.ndarray, lats: np.ndarray, vals: np.ndarray,
         glon: np.ndarray, glat: np.ndarray, power: float = 2.0):
    """Inverse Distance Weighting como respaldo cuando el variograma no ajusta."""
    gl, ga = np.meshgrid(glon, glat)
    z = np.empty_like(gl, dtype=float)
    var = np.empty_like(gl, dtype=float)
    for i in range(gl.shape[0]):
        for j in range(gl.shape[1]):
            d = np.sqrt((lons - gl[i, j]) ** 2 + (lats - ga[i, j]) ** 2)
            if np.any(d < 1e-9):
                k = int(np.argmin(d))
                z[i, j] = vals[k]
                var[i, j] = 0.0
                continue
            w = 1.0 / d ** power
            w /= w.sum()
            z[i, j] = float(np.sum(w * vals))
            # varianza ponderada como proxy de incertidumbre
            var[i, j] = float(np.sum(w * (vals - z[i, j]) ** 2))
    return z, var


def _build_ok(lons, lats, vals, modelo: str = "exponential"):
    """
    Construye un OrdinaryKriging con variograma robusto frente a degeneracion.

    Con pocas estaciones y un outlier, el autoajuste de PyKrige a veces converge a un
    variograma con range microescala (range << separacion tipica entre estaciones).
    Eso vuelve a todas las estaciones mutuamente descorrelacionadas: el Kriging les
    asigna peso uniforme y colapsa a la media global, produciendo un campo plano (el
    caso observado en SO2: range ajustado de 0,0002 grados frente a estaciones a
    0,05 grados). Cuando se detecta esa degeneracion se impone un variograma esferico
    con range igual a la separacion mediana entre estaciones (escala urbana de Cali),
    sill igual a la varianza muestral y nugget del 15%. Si el autoajuste es sano
    (caso O3: range de 0,18 grados) no se interviene.
    """
    from pykrige.ok import OrdinaryKriging
    from scipy.spatial.distance import pdist

    pares = pdist(np.column_stack([lons, lats]))
    d_med = float(np.median(pares)) if pares.size else 0.02
    val_var = float(np.var(vals))

    ok = OrdinaryKriging(
        lons, lats, vals, variogram_model=modelo,
        enable_plotting=False, coordinates_type="geographic", pseudo_inv=True,
    )
    params = ok.variogram_model_parameters
    # Modelos con sill: [psill, range, nugget]. range esta en la posicion 1.
    rng = float(params[1]) if len(params) >= 3 else None
    if rng is not None and val_var > 1e-9 and rng < 0.25 * d_med:
        fixed = {"sill": val_var, "range": d_med, "nugget": 0.15 * val_var}
        ok = OrdinaryKriging(
            lons, lats, vals, variogram_model="spherical",
            variogram_parameters=fixed, enable_plotting=False,
            coordinates_type="geographic", pseudo_inv=True,
        )
    return ok


def kriging_ordinario(lons, lats, vals, glon, glat,
                      modelo: str = "exponential"):
    """
    Kriging Ordinario 2D sobre estaciones puntuales -> grilla.

    Devuelve (z, sigma) donde z es la superficie estimada y sigma la desviacion
    de prediccion Kriging (raiz de la varianza). Con muy pocos puntos el ajuste
    del variograma puede fallar; en ese caso cae a IDW y reporta un sigma proxy.

    lons, lats, vals : arrays 1D de las estaciones (mismo largo).
    glon, glat       : ejes 1D de la grilla de salida.
    """
    lons = np.asarray(lons, float)
    lats = np.asarray(lats, float)
    vals = np.asarray(vals, float)
    ok_fit = np.isfinite(vals)
    lons, lats, vals = lons[ok_fit], lats[ok_fit], vals[ok_fit]

    if vals.size < 3:
        # Insuficiente para variograma: IDW (o campo uniforme si 1 punto).
        if vals.size == 0:
            gl, ga = np.meshgrid(glon, glat)
            return np.full_like(gl, np.nan, dtype=float), np.full_like(gl, np.nan, dtype=float)
        z, var = _idw(lons, lats, vals, glon, glat)
        return z, np.sqrt(np.clip(var, 0, None))

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            ok = _build_ok(lons, lats, vals, modelo)
            z, ss = ok.execute("grid", glon, glat)
        z = np.asarray(z, float)
        sigma = np.sqrt(np.clip(np.asarray(ss, float), 0, None))
        if not np.all(np.isfinite(z)):
            raise ValueError("Kriging produjo valores no finitos")
        # Red de seguridad: si el campo sigue plano pese a datos con varianza, IDW.
        if np.var(vals) > 1e-9 and float(np.std(z)) < 1e-6:
            raise ValueError("Kriging colapsado a campo plano")
        return z, sigma
    except Exception:
        z, var = _idw(lons, lats, vals, glon, glat)
        return z, np.sqrt(np.clip(var, 0, None))


# ---------------------------------------------------------------------------
# Validacion Leave-One-Station-Out
# ---------------------------------------------------------------------------

@dataclass
class LooMetrics:
    rmse: float
    mae: float
    r2: float
    bias: float
    n: int


def loo_cv(lons, lats, vals, modelo: str = "exponential") -> dict:
    """
    Leave-One-Station-Out: para cada estacion se reentrena el Kriging con las
    demas y se predice la retenida. Devuelve por-estacion el error y, en la clave
    'global', las metricas agregadas (RMSE, MAE, R2, bias) sobre todos los folds.

    lons, lats, vals : arrays 1D por estacion. Se asume un valor por estacion
    (ej. el promedio temporal o el forecast). Indice i identifica la estacion.
    """
    lons = np.asarray(lons, float)
    lats = np.asarray(lats, float)
    vals = np.asarray(vals, float)
    n = vals.size
    pred = np.full(n, np.nan)

    if n >= 3:
        for i in range(n):
            mask = np.arange(n) != i
            zi = _krig_punto(lons[mask], lats[mask], vals[mask],
                             lons[i], lats[i], modelo)
            pred[i] = zi

    obs = vals
    resid = pred - obs
    ok = np.isfinite(resid)
    per_station = resid

    if ok.sum() >= 2:
        rmse = float(np.sqrt(np.mean(resid[ok] ** 2)))
        mae = float(np.mean(np.abs(resid[ok])))
        bias = float(np.mean(resid[ok]))
        ss_res = float(np.sum(resid[ok] ** 2))
        ss_tot = float(np.sum((obs[ok] - np.mean(obs[ok])) ** 2))
        r2 = float(1.0 - ss_res / ss_tot) if ss_tot > 1e-12 else float("nan")
    else:
        rmse = mae = bias = r2 = float("nan")

    return {
        "global": LooMetrics(rmse, mae, r2, bias, int(ok.sum())),
        "pred": pred,
        "resid": per_station,
    }


def _krig_punto(lons, lats, vals, qlon, qlat, modelo):
    """Kriging para un unico punto de consulta (usado en LOO-CV).

    Usa el mismo variograma robusto que el mapa (_build_ok) para que la validacion
    LOO-CV y la superficie servida sean metodologicamente consistentes.
    """
    if vals.size < 3:
        d = np.sqrt((lons - qlon) ** 2 + (lats - qlat) ** 2)
        w = 1.0 / np.clip(d, 1e-9, None) ** 2
        return float(np.sum(w * vals) / np.sum(w))
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            ok = _build_ok(lons, lats, vals, modelo)
            z, _ = ok.execute("points", np.array([qlon]), np.array([qlat]))
        return float(z[0])
    except Exception:
        d = np.sqrt((lons - qlon) ** 2 + (lats - qlat) ** 2)
        w = 1.0 / np.clip(d, 1e-9, None) ** 2
        return float(np.sum(w * vals) / np.sum(w))


# ---------------------------------------------------------------------------
# Indice de Moran global sobre la superficie predicha
# ---------------------------------------------------------------------------

def moran_global(z: np.ndarray) -> dict:
    """
    Indice de Moran global I sobre una grilla regular (vecindad rook), con prueba
    de permutacion. Cuantifica si la superficie tiene coherencia espacial (I alto)
    o ruido (I cerca de 0). Devuelve I, p-value y conteo de celdas.
    """
    z = np.asarray(z, float)
    try:
        from libpysal.weights import lat2W
        from esda.moran import Moran
        nrow, ncol = z.shape
        w = lat2W(nrow, ncol, rook=True)
        flat = z.ravel()
        ok = np.isfinite(flat)
        if ok.sum() < 0.5 * flat.size:
            return {"I": float("nan"), "p": float("nan"), "n": int(ok.sum())}
        flat = np.where(np.isfinite(flat), flat, np.nanmean(flat))
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            mi = Moran(flat, w, permutations=999)
        return {"I": float(mi.I), "p": float(mi.p_sim), "n": int(flat.size)}
    except Exception as exc:  # pragma: no cover
        return {"I": float("nan"), "p": float("nan"), "n": 0, "error": str(exc)}
