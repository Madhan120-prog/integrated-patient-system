"""Our own 3D U-Net, written out so every part is visible.

Shape of the idea (the "U"):
    encoder: look at the scan, shrink it step by step, learning WHAT is there
    decoder: grow it back step by step, learning WHERE it is
    skips:   copy fine detail from each encoder level straight across to the decoder,
             so edges stay sharp after shrinking

Choices borrowed from nnU-Net (they are the tested defaults):
    InstanceNorm + LeakyReLU, two 3x3x3 convolutions per level, channels double each level.
Choice made for THIS data:
    our slices are 3 mm apart but pixels are ~1 mm, so the first shrink is in-plane only
    (1,2,2). After it the voxels are ~2 x 2 x 3 mm, close to cubes, and later shrinks are (2,2,2).
"""
import torch
from torch import nn


class Block(nn.Sequential):
    """Two rounds of: 3x3x3 convolution -> normalise -> activation."""

    def __init__(self, cin, cout):
        super().__init__(
            nn.Conv3d(cin, cout, 3, padding=1), nn.InstanceNorm3d(cout, affine=True), nn.LeakyReLU(0.01, inplace=True),
            nn.Conv3d(cout, cout, 3, padding=1), nn.InstanceNorm3d(cout, affine=True), nn.LeakyReLU(0.01, inplace=True),
        )


class UNet3D(nn.Module):
    def __init__(self, in_ch=1, n_classes=2, base=16, strides=((1, 2, 2), (2, 2, 2), (2, 2, 2))):
        super().__init__()
        ch = [base * 2 ** i for i in range(len(strides) + 1)]          # e.g. 16, 32, 64, 128
        self.enc = nn.ModuleList([Block(in_ch, ch[0])] + [Block(ch[i], ch[i + 1]) for i in range(len(strides))])
        self.pool = nn.ModuleList([nn.MaxPool3d(s) for s in strides])
        self.up = nn.ModuleList([nn.ConvTranspose3d(ch[i + 1], ch[i], s, stride=s) for i, s in enumerate(strides)])
        self.dec = nn.ModuleList([Block(2 * ch[i], ch[i]) for i in range(len(strides))])
        self.head = nn.Conv3d(ch[0], n_classes, 1)                      # one score per class per voxel

    def forward(self, x):
        skips = []
        for i, enc in enumerate(self.enc):
            x = enc(x)
            if i < len(self.pool):
                skips.append(x)
                x = self.pool[i](x)
        for i in reversed(range(len(self.up))):
            x = self.dec[i](torch.cat([self.up[i](x), skips[i]], dim=1))
        return self.head(x)


if __name__ == "__main__":
    net = UNet3D()
    out = net(torch.zeros(1, 1, 32, 128, 128))          # (batch, channel, z, y, x)
    assert out.shape == (1, 2, 32, 128, 128), out.shape
    print(f"ok: output {tuple(out.shape)}, {sum(p.numel() for p in net.parameters()) / 1e6:.2f} M parameters")
