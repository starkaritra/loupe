"""Render LaTeX (matplotlib mathtext) → transparent PNG, offline & cached. $0, no services.

Loupe shows real equations as crisp holographic images: each formula is rendered once to
assets/eqn/<hash>.png and reused. The engine loads these by hash. Add equations to EQUATIONS and
re-run: `python tools/render_equations.py`.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

OUT = Path(__file__).resolve().parent.parent / "assets" / "eqn"
ACCENT = "#bfe8ff"

# id -> LaTeX (mathtext subset). Holographic cyan on transparent; engine tints/glows as needed.
EQUATIONS = {
    "attention": r"$\mathrm{Attn}=\mathrm{softmax}\!\left(\frac{QK^{\top}}{\sqrt{d_k}}\right)V$",
    "scores": r"$s_{ij}=q_i\cdot k_j^{\top}$",
    "softmax": r"$a_{ij}=\frac{e^{s_{ij}}}{\sum_j e^{s_{ij}}}$",
    "mlp": r"$y=\mathrm{GELU}(xW_1)\,W_2$",
    "layernorm": r"$\hat{x}=\frac{x-\mu}{\sigma}\,\gamma+\beta$",
    "residual": r"$x \leftarrow x+\mathrm{sub}(\mathrm{LN}(x))$",
    "embed": r"$x = E[t]+P[p]$",
    "qkv": r"$Q,K,V = xW_Q,\,xW_K,\,xW_V$",
    "concat": r"$O=\mathrm{concat}(h_1..h_{12})\,W_O$",
    "conv": r"$y=\mathrm{ReLU}(W*x+b)$",
    "pool": r"$y_{ij}=\max_{p,q}\,x_{i+p,\,j+q}$",
    "fc": r"$y=\mathrm{ReLU}(Wx+b)$",
    "lstm_f": r"$f_t=\sigma(W_f[h_{t-1},x_t])$",
    "lstm_i": r"$i_t=\sigma(W_i\cdot),\ \tilde c=\tanh(W_c\cdot)$",
    "lstm_c": r"$c_t=f_t c_{t-1}+i_t\tilde c_t$",
    "lstm_o": r"$h_t=o_t\odot\tanh(c_t)$",
    "clip": r"$c=\mathrm{CLIP}_\mathrm{text}(\mathrm{prompt})$",
    "unet": r"$\epsilon_\theta(z_t,t,c)$",
    "vae": r"$x=\mathcal{D}(z_0)$",
    "diffuse": r"$z_{t-1}=z_t-\epsilon_\theta$",
    "ssm": r"$h_t=\bar A h_{t-1}+\bar B x_t,\ y=Ch_t$",
    "mamba_gate": r"$y=\mathrm{SSM}(x)\odot\sigma(xW)$",
    "vae_enc": r"$\mu,\sigma=\mathrm{Enc}(x)$",
    "vae_z": r"$z=\mu+\sigma\odot\epsilon,\ \epsilon\sim\mathcal{N}(0,I)$",
    "gan_g": r"$x=G(z),\ z\sim\mathcal{N}(0,I)$",
    "gan_d": r"$D(x)\in[0,1]$",
    "mlm": r"$P(\mathrm{[MASK]})=\mathrm{softmax}(W h)$",
    "router": r"$g=\mathrm{top\text{-}k}\,\mathrm{softmax}(xW_r)$",
    "cross_attn": r"$\mathrm{softmax}(Q_{dec}K_{enc}^{\top}/\sqrt{d})V_{enc}$",
}


def render(latex: str, path: Path, fs: int = 40) -> None:
    fig = plt.figure(figsize=(0.1, 0.1))
    fig.text(0, 0, latex, fontsize=fs, color=ACCENT)
    fig.savefig(path, dpi=200, transparent=True, bbox_inches="tight", pad_inches=0.12)
    plt.close(fig)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    index = {}
    for key, latex in EQUATIONS.items():
        h = hashlib.sha256(latex.encode()).hexdigest()[:12]
        png = OUT / f"{h}.png"
        if not png.exists():
            render(latex, png)
        index[key] = png.name
    (OUT / "index.json").write_text(json.dumps(index, indent=2), encoding="utf-8")
    print("rendered", len(index), "equations ->", OUT)


if __name__ == "__main__":
    main()
