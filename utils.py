from collections import Counter, defaultdict
import more_itertools
import random
from tqdm import tqdm
from scipy.sparse import csr_matrix
import numpy as np
import pandas as pd
from pathlib import Path
import json
import random
from sklearn.utils import shuffle
from sklearn.model_selection import train_test_split
import pickle
from pathlib import Path
import os
import matplotlib.pyplot as plt
import copy
import itertools



def sequential_groupby(dataframe, idx_column, other_columns):
    """dataframe groupby assuming column values are sequential. returns rows in order entered.
    
    Arguments:
        dataframe
        idx_column string -- dataframe column id to group by. must be sequential
        other_columns list(string) -- columns to save in output.
    
    Returns:
        list -- grouped rows
    """
    dataset = {}
    cur_id = dataframe[idx_column][0]
    cur_group = []
    for row_id, row in zip(dataframe[idx_column], zip(*[dataframe[column].values.tolist() for column in other_columns])):
        if cur_id == row_id:
            cur_group.append(row)
        else:
            dataset[cur_id] = cur_group

            cur_group = [row]
            cur_id = row_id

    dataset[cur_id] = cur_group

    return dataset

def contiguize_column(dataframe, column, keymap=None):
    """turns the keys in a dataframe column into indexes
    
    Arguments:
        dataframe dataframe -- dataframe
        column string -- column name
        keymap dict -- column key map generated from previous run (default: {None})
    """

    print(f"contiguizing column {column}")
    if keymap == None:
        keymap = {}
    
    noncontiguous_keys = dataframe[column].unique()
    
    cur_index = max(keymap.values(), default=-1)+1
    for key in noncontiguous_keys:
        if key not in keymap:
            keymap[key] = cur_index
            cur_index+= 1
    
    f = lambda key: keymap[key]
    dataframe[column] = dataframe[column].apply(f)

    return dataframe, keymap



def contiguize_keys(*datasets):
    keymap = {}
    print("contiguizing keys")
    for X, y in datasets:
        build_contiguized_keymap(X, keymap)
        build_contiguized_keymap([y], keymap)
    return [([np.array([keymap[xi] for xi in sess]) for sess in X], 
        np.array([keymap[yi] for yi in y])) for X, y in datasets]

def save_accs(location, acc_lists, plt_kwargs):
    location.mkdir(parents=True, exist_ok=True)
    savedir = Path(location)
    plt.clf()
    plt.title(plt_kwargs["title"])
    if "xlabel" in plt_kwargs:
        plt.xlabel(plt_kwargs["xlabel"])
    if "ylabel" in plt_kwargs:
        plt.ylabel(plt_kwargs["ylabel"])
    
    plots = []
    if "legend" in plt_kwargs:
        for desc, acc_list in zip(plt_kwargs["legend"], acc_lists):
            plots.append(plt.plot(acc_list, label=desc))
        plt.legend()
    
    else:
        for acc_list in acc_lists:
            plots.append(plt.plot(acc_list))
    
    plt.savefig(savedir/(plt_kwargs["title"]+".png"))



def mask_length(sessions, maskoff_vals=0, maskon_vals=1):
    """take sessions, turn it into a numpy array and create a mask to ignore portions of sessions that don't matter
    
    Arguments:
        sessions {list of variable length list of items} -- the sessions to turn into a numpy array. between each session, all dimensions must agree except the second
    
    Keyword Arguments:
        maskoff_vals {int} -- values to use in mask for session items that don't exist (default: {0})
        maskon_vals {int} -- values to use in mask for session items that exist (default: {1})

    Returns:
        sessions_array, mask -- sessions as a numpy array and the mask
    """
    item_shape = sessions[0].shape
    num_sessions = len(sessions)
    sess_lengths = [len(sess) for sess in sessions]
    max_sess_len = int((max(sess_lengths)+3)/4)*4 # cutting the amount of retracing in half

    mask_bool = np.arange(max_sess_len).reshape(-1, max_sess_len).repeat(num_sessions, axis=0)
    mask_bool = mask_bool < np.array(sess_lengths).reshape(num_sessions, -1)
    mask = np.zeros(mask_bool.shape, np.float32)
    mask[mask_bool == 1] = maskon_vals
    mask[mask_bool == 0] = maskoff_vals

    sessions_array = np.zeros([num_sessions, max_sess_len]+list(item_shape[1:]), dtype=sessions[0].dtype)
    for length, i in zip(sess_lengths, range(num_sessions)):
        sessions_array[i, :length] = sessions[i]

    return sessions_array, mask

def train_val_test_split(*Xs, train_perc=.64, val_perc=.16, test_perc=.2):
    print(f"train_val_test_split @ {train_perc} train, {val_perc} val, {test_perc} test")
    assert(train_perc+val_perc+test_perc == 1)
    num_elems = len(Xs[0])

    train_cutoff = int(num_elems*train_perc)
    val_cutoff = int(num_elems*(train_perc+val_perc))
    test_cutoff = int(num_elems*(train_perc+val_perc+test_perc))

    split_Xs = [(X[:train_cutoff], X[train_cutoff:val_cutoff], X[val_cutoff:test_cutoff]) for X in Xs]

    train = [X[0] for X in split_Xs]
    val = [X[1] for X in split_Xs]
    test = [X[2] for X in split_Xs]

    return train, val, test

def batchify(*args, batch_size=1000, arg_len=None, shuffle=False):
    if batch_size == -1:
        yield args
    if shuffle:
        args = list(zip(*args))
        random.shuffle(args)
        args = list(zip(*args))
    num_elems = len(args[0]) if arg_len == None else arg_len
    for i in range(0, num_elems, batch_size):
        yield [arg[i: i+batch_size] for arg in args]

def flatten(list_of_lists):
    return itertools.chain.from_iterable(list_of_lists)

class keyed_defaultdict(defaultdict):
    def __missing__(self, key):
        if self.default_factory is None:
            raise KeyError( key )
        else:
            ret = self[key] = self.default_factory(key)
            return ret
