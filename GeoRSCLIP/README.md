---
license: cc
datasets:
- Zilun/RS5M
language:
- en
metrics:
- accuracy
- recall
---
## GeoRSCLIP Model
* **GeoRSCLIP with ViT-B-32 and ViT-H-14 backbone**
* **GeoRSCLIP-FT for retrieval**


### Installation

* Install Pytorch following instructions from the official website (We tested in torch 2.0.1 with CUDA 11.8 and 2.1.0 with CUDA 12.1)

```bash
  pip install torch==2.0.1 torchvision==0.15.2 torchaudio==2.0.2 --index-url https://download.pytorch.org/whl/cu118
```

* Install other dependencies

```bash
  pip install pillow pandas scikit-learn ftfy tqdm matplotlib transformers adapter-transformers open_clip_torch pycocotools timm clip-benchmark torch-rs
```

### Usage

* Clone the repo from: https://huggingface.co/Zilun/GeoRSCLIP

```bash
git clone https://huggingface.co/Zilun/GeoRSCLIP
cd GeoRSCLIP
```

* Unzip the test data
```bash
unzip data/rs5m_test_data.zip
```

* Run the inference script:
```bash
  python codebase/inference.py --ckpt-path /your/local/path/to/RS5M_ViT-B-32.pt --test-dataset-dir /your/local/path/to/rs5m_test_data
```

* (Optional) If you just want to load the GeoRSCLIP model:

```python

  import open_clip
  import torch
  from inference_tool import get_preprocess


  ckpt_path = "/your/local/path/to/RS5M_ViT-B-32.pt"
  model, _, _ = open_clip.create_model_and_transforms("ViT-B/32", pretrained="openai")
  checkpoint = torch.load(ckpt_path, map_location="cpu")
  msg = model.load_state_dict(checkpoint, strict=False)
  model = model.to("cuda")
  img_preprocess = get_preprocess(
        image_resolution=224,
  )
```

```python

  import open_clip
  import torch
  from inference_tool import get_preprocess

  ckpt_path = "/your/local/path/to/RS5M_ViT-H-14.pt"
  model, _, _ = open_clip.create_model_and_transforms("ViT-H/14", pretrained="laion2b_s32b_b79k")
  checkpoint = torch.load(ckpt_path, map_location="cpu")
  msg = model.load_state_dict(checkpoint, strict=False)
  model = model.to("cuda")
  img_preprocess = get_preprocess(
        image_resolution=224,
  )
```