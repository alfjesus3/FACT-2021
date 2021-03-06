import argparse
import torch
import os
import numpy as np
from matplotlib import pyplot as plt
from utils import str2bool, mkdirs
import time
import json


def extract_train_metrics(json_path, iters_lim, n_samples_aver=10):
    """ It receives the path to the json file with the metrics and plots them  """
    iters = []
    vae_loss = []
    D_loss = []
    recon = []
    tc = []

    lst = json.load(open(json_path, mode="r"))
    aver_vae, aver_D, aver_recon, aver_tc = 0, 0, 0, 0
    for di in lst:
        assert isinstance(di, dict), "Got unexpected variable type"
        if di.get("vae_loss") is not None:
            if di.get("its") <= iters_lim:
                if di.get("its") % 1000 == 0:
                    iters.append(di["its"])
                    vae_loss.append(aver_vae/n_samples_aver)
                    D_loss.append(aver_D/n_samples_aver)
                    recon.append(aver_recon/n_samples_aver)
                    tc.append(aver_tc/n_samples_aver)
                    aver_vae, aver_D, aver_recon, aver_tc = 0, 0, 0, 0
                else:
                    aver_vae += di["vae_loss"]
                    aver_D += di["D_loss"]
                    aver_recon += di["recon_loss"]
                    aver_tc += di["tc_loss"]

    return iters, recon, tc


def plot_train_loss(ckpt_dir, seeds, gammas, lambdas, max_iters, detail):
    """ Given the root folder it extracts and plots the tc_loss and recon_loss over the training """
    subdirs = [x[1] for x in os.walk(ckpt_dir)]
    subdirs = subdirs[0]

    vanilla = 'vanilla' in ckpt_dir
    gammas = ['ga_'+str(i) for i in gammas]
    lambdas = ['la_'+str(i) for i in lambdas]

    fig2, axs = plt.subplots(nrows=2, ncols=1)
    for subdir in subdirs:
        if seeds[0] in subdir:
            idx0 = subdir.index('seed')
            aver_recon, aver_tc, iters = [], [], []
            for seed in seeds:
                if any(ga in subdir for ga in gammas):
                    if vanilla or any(lam in subdir for lam in lambdas):
                        path = os.path.join(ckpt_dir, subdir[:idx0]+seed, "metrics.json")
                        iters, recon_loss, tc_loss = extract_train_metrics(path, max_iters)
                        if len(aver_recon) == 0:
                            aver_recon = np.zeros_like(recon_loss)
                            aver_tc = np.zeros_like(tc_loss)
                        aver_recon += recon_loss
                        aver_tc += tc_loss
            if len(aver_recon) != 0:
                aver_recon = aver_recon / len(seeds)
                idx1 = subdir.index('_ga')
                idx2 = subdir.index('_iters')
                aver_tc = aver_tc / len(seeds)
                axs[0].plot(iters, aver_recon, label=subdir[idx1+1:idx2])
                axs[1].plot(iters, aver_tc, label=subdir[idx1+1:idx2])
    axs[0].legend(loc='center left', bbox_to_anchor=(1, 0.5), ncol=2)
    axs[1].legend(loc='center left', bbox_to_anchor=(1, 0.5), ncol=2)
    if detail:
        axs[0].set_ylim([0, 150])
        axs[1].set_ylim([-0.3, 0.85])
        fig2.set_figheight(6)
        fig2.set_figwidth(8)
    axs[1].set_xlabel("iterations")
    axs[0].set_ylabel("reconstruction loss")
    axs[1].set_ylabel("true total correlation (VAE)")


def extract_disentanglement_metric(json_path, max_iters):
    """ It receives the path to the json file and plots the proposed metric results  """
    iters, scores = [], []
    # Adding initial measure
    iters.append(0)
    scores.append(0)
    final_recon_loss = -1

    lst = json.load(open(json_path, mode="r"))
    for di in lst:
        assert isinstance(di, dict), "Got unexpected variable type"

        if di.get("its") <= max_iters:
            if di.get("metric_score") is not None:
                iters.append(di["its"])
                scores.append(di["metric_score"])
            else:
                final_recon_loss = di["recon_loss"]

    return iters, scores, final_recon_loss


def plot_disentanglemet(ckpt_dir, seeds, gammas, lambdas, max_iters, detail):
    """ Given the root folder it extracts and plots the disentanglement metric """
    subdirs = [x[1] for x in os.walk(ckpt_dir)]
    subdirs = subdirs[0]

    vanilla = 'vanilla' in ckpt_dir
    gammas = ['ga_'+str(i) for i in gammas]
    lambdas = ['la_'+str(i) for i in lambdas]

    fig1 = plt.figure(figsize=(9, 4))
    ax1 = plt.subplot(1, 1, 1)
    last_scores = []
    for subdir in subdirs:
        if seeds[0] in subdir:
            idx0 = subdir.index('seed')
            aver_disent, aver_recon, iters = [], [], []
            for seed in seeds:
                if any(ga in subdir for ga in gammas):
                    if vanilla or any(lam in subdir for lam in lambdas):
                        path = os.path.join(ckpt_dir, subdir[:idx0]+seed, "metrics.json")
                        iters, disent_vals, recon_loss = extract_disentanglement_metric(path, max_iters)
                        if len(aver_disent) == 0:
                            aver_disent = np.zeros_like(disent_vals)
                            aver_recon = np.zeros_like(recon_loss)
                        aver_disent += disent_vals
                        aver_recon += recon_loss
            if len(aver_disent) != 0:
                idx1 = subdir.index('_ga')
                idx3 = subdir.index('_iters')
                if not vanilla:
                    idx2 = subdir.index('_la')
                else:
                    idx2 = idx3
                aver_disent = aver_disent / len(seeds)
                aver_recon = aver_recon / len(seeds)
                last_scores.append((aver_disent[-1], aver_recon, int(subdir[idx1+4:idx2])))
                ax1.plot(iters, aver_disent, label=subdir[idx1+1:idx3])
        if detail:
            plt.ylim([0.4, 1.0])
        else:
            plt.ylim([0, 1.0])
        ax1.legend(loc='upper center', bbox_to_anchor=(0.5, 1.15), ncol=5)
        ax1.set_xlabel("iterations")
        ax1.set_ylabel("disentanglement metric")


def get_comparison_plot(scores_van, scores_ad):
    """ It aims to reproduce the results observed in Figure 8 (For FactorVAE and AD-FactorVAE) """
    model1_distang = [0.69, 0.685, 0.73, 0.700, 0.625, 0.68]
    model1_reconErr = [20, 30, 42, 58, 60, 111]
    model1_value = [1,2,4,6,8,16]

    # The values were updated from trained vanilla folder
    model2_distang = [x[0] for x in scores_van]
    model2_reconErr = [x[1] for x in scores_van]
    model2_value = [x[2] for x in scores_van]

    # The values were updated from trained AD folder
    model3_distang = [x[0] for x in scores_ad]
    model3_reconErr = [x[1] for x in scores_ad]
    model3_value = [x[2] for x in scores_ad]

    fig, ax = plt.subplots()

    ax.scatter(model1_reconErr, model1_distang, marker="o", c='b', label='beta VAE')
    for i, txt in enumerate(model1_value):
        ax.annotate(txt, (model1_reconErr[i], model1_distang[i]), size=12)

    ax.scatter(model2_reconErr, model2_distang, marker="o", c='g', label='Factor VAE')
    for i, txt in enumerate(model2_value):
        ax.annotate(txt, (model2_reconErr[i], model2_distang[i]), size=12)

    ax.scatter(model3_reconErr, model3_distang, marker="o", c='r', label='AD Factor VAE')
    for i, txt in enumerate(model3_value):
        ax.annotate(txt, (model3_reconErr[i], model3_distang[i]), size=12)

    plt.rc('axes', labelsize=8)
    ax.legend(loc="upper right" )
    ax.set_title('Reconstruction error against disentanglement metric ', size = 13)
    ax.set_xlabel('reconstruction error', size = 15)
    ax.set_ylabel('disentanglement metric', size = 15)
    plt.xlim([0, 150])
    plt.ylim([0.3, 1])
    plt.grid(color='r', linestyle=':', linewidth=0.5)


def plot_comparison_methods(ckpt_dirs, seeds, gammass, lambdass, max_iters):

    scores_per_ckpt = []
    for i in range(len(ckpt_dirs)):
        ckpt_dir = ckpt_dirs[i]
        subdirs = [x[1] for x in os.walk(ckpt_dir)]
        subdirs = subdirs[0]

        vanilla = 'vanilla' in ckpt_dir
        gammas = gammass[i]
        gammas = ['ga_'+str(i) for i in gammas]
        lambdas = lambdass[i]
        lambdas = ['la_'+str(i) for i in lambdas]

        last_scores = []
        for subdir in subdirs:
            if seeds[0] in subdir:
                idx0 = subdir.index('seed')
                aver_disent, aver_recon = [], []
                for seed in seeds:
                    if any(ga in subdir for ga in gammas):
                        if vanilla or any(lam in subdir for lam in lambdas):
                            path = os.path.join(ckpt_dir, subdir[:idx0]+seed, "metrics.json")
                            _, disent_vals, recon_loss = extract_disentanglement_metric(path, max_iters)
                            if len(aver_disent) == 0:
                                aver_disent = np.zeros_like(disent_vals)
                                aver_recon = np.zeros_like(recon_loss)
                            aver_disent += disent_vals
                            aver_recon += recon_loss
                if len(aver_disent) != 0:
                    idx1 = subdir.index('_ga')
                    idx3 = subdir.index('_iters')
                    if not vanilla:
                        idx2 = subdir.index('_la')
                    else:
                        idx2 = idx3
                    aver_disent = aver_disent / len(seeds)
                    aver_recon = aver_recon / len(seeds)
                    last_scores.append((aver_disent[-1], aver_recon, int(subdir[idx1+4:idx2])))
        scores_per_ckpt.append(last_scores)

    # Get plot
    get_comparison_plot(scores_per_ckpt[0], scores_per_ckpt[1])
