# Copyright (c) Meta Platforms, Inc. All Rights Reserved
import torch.nn as nn
from adain_test.adain_2 import adaptive_instance_normalization as adain

###############################
############ Layers ###########
###############################


class MLPblock(nn.Module):
    def __init__(self, dim, seq0, seq1, first=False, w_embed=True, style_code_dim = 256):
        super().__init__()

        self.w_embed = w_embed
        self.fc0 = nn.Conv1d(seq0, seq1, 1)

        if self.w_embed:
            if first:
                self.conct = nn.Linear(dim * 2+style_code_dim, dim)
            else:
                self.conct = nn.Identity()
            self.emb_fc = nn.Linear(dim, dim)

        self.fc1 = nn.Linear(dim, dim)
        self.norm0 = nn.LayerNorm(dim)
        self.norm1 = nn.LayerNorm(dim)
        self.act = nn.SiLU()

    def forward(self, inputs):

        if self.w_embed:
            x = inputs[0]
            embed = inputs[1]
            x = self.conct(x) + self.emb_fc(self.act(embed))
        else:
            x = inputs

        x_ = self.norm0(x)
        x_ = self.fc0(x_)
        x_ = self.act(x_)
        x = x + x_

        x_ = self.norm1(x)
        x_ = self.fc1(x_)
        x_ = self.act(x_)

        x = x + x_

        if self.w_embed:
            return x, embed
        else:
            return x


class MLPblock_adain(nn.Module):
    def __init__(self, dim, seq0, seq1, first=False, w_embed=True):
        super().__init__()

        self.w_embed = w_embed
        self.fc0 = nn.Conv1d(seq0, seq1, 1)

        if self.w_embed:
            if first:
                self.conct = nn.Linear(dim * 2, dim)
            else:
                self.conct = nn.Identity()
            self.emb_fc = nn.Linear(dim, dim)

        self.fc1 = nn.Linear(dim, dim)
        self.norm0 = nn.LayerNorm(dim)
        self.norm1 = nn.LayerNorm(dim)
        self.act = nn.SiLU()

    def forward(self, inputs):


        x = inputs[0]
        embed = inputs[1]
        style_code = inputs[2]
        alpha = 1.0
        adain_input = self.conct(x)
        # adain 
        tmp = adain(adain_input, style_code)
        tmp = alpha * tmp + (1 - alpha) * adain_input

        x = tmp + self.emb_fc(self.act(embed))


        x_ = self.norm0(x)
        x_ = self.fc0(x_)
        x_ = self.act(x_)
        x = x + x_

        x_ = self.norm1(x)
        x_ = self.fc1(x_)
        x_ = self.act(x_)

        x = x + x_

        if self.w_embed:
            return x, embed, style_code
        else:
            return x

class BaseMLP(nn.Module):
    def __init__(self, dim, seq, num_layers, w_embed=True, style_code_dim = 256):
        super().__init__()

        layers = []
        for i in range(num_layers):
            layers.append(
                MLPblock(dim, seq, seq, first=i == 0 and w_embed, w_embed=w_embed, style_code_dim=style_code_dim)
            )

        self.mlps = nn.Sequential(*layers)

    def forward(self, x):
        x = self.mlps(x)
        return x

class BaseMLP_adain(nn.Module):
    def __init__(self, dim, seq, num_layers, w_embed=True):
        super().__init__()

        layers = []
        for i in range(num_layers):
            layers.append(
                MLPblock_adain(dim, seq, seq, first=i == 0 and w_embed, w_embed=w_embed)
            )

        self.mlps = nn.Sequential(*layers)

    def forward(self, x):
        # print(len(x))
        x = self.mlps(x)

        # x = self.mlps(inputs = x, style_code = style_code)
        return x

###############################
########### Networks ##########
###############################


class DiffMLP(nn.Module):
    def __init__(self, latent_dim=512, seq=98, num_layers=12, style_code_dim = 256):
        super(DiffMLP, self).__init__()

        self.motion_mlp = BaseMLP(dim=latent_dim, seq=seq, num_layers=num_layers, style_code_dim=style_code_dim)

    def forward(self, motion_input, embed):

        motion_feats = self.motion_mlp([motion_input, embed])[0]

        return motion_feats


class DiffMLP_adain(nn.Module):
    def __init__(self, latent_dim=512, seq=98, num_layers=12):
        super(DiffMLP_adain, self).__init__()

        self.motion_mlp = BaseMLP_adain(dim=latent_dim, seq=seq, num_layers=num_layers)

    def forward(self, motion_input, embed, style_code):

        motion_feats = self.motion_mlp([motion_input, embed, style_code])[0]

        return motion_feats


class PureMLP(nn.Module):
    def __init__(
        self, latent_dim=512, seq=98, num_layers=12, input_dim=54, output_dim=132
    ):
        super(PureMLP, self).__init__()

        self.input_fc = nn.Linear(input_dim, latent_dim)
        self.motion_mlp = BaseMLP(
            dim=latent_dim, seq=seq, num_layers=num_layers, w_embed=False
        )
        self.output_fc = nn.Linear(latent_dim, output_dim)

    def forward(self, motion_input):

        motion_feats = self.input_fc(motion_input)
        motion_feats = self.motion_mlp(motion_feats)
        motion_feats = self.output_fc(motion_feats)

        return motion_feats
