#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import numpy as np
import torch
# from collections import Counter
# import subprocess as sp
# import time
# from utils.random_utils import random_index
# from utils.extract_movement import MOVEMENT
from src.lib.NeighConst import neighconst

'''
description: 
 get all movement files under the dir 'workDir'
 author: wuxingxing
'''
def collect_all_sourcefiles(workDir, sourceFileName="MOVEMENT"):
    movement_dir = []
    if not os.path.exists(workDir):
        raise FileNotFoundError(workDir + "  does not exist")
    
    # added followlinks = True to support softlinks
    # get dir of movements
    for path, dirList, fileList in os.walk(workDir, followlinks=True):
        if sourceFileName in fileList:
            movement_dir.append(os.path.abspath(path))
    return movement_dir
""" ********************************************* disuse **********************************
def gen_config_inputfile(config):
    output_path = os.path.join(config["dRFeatureInputDir"], "gen_dR_feature.in")
    with open(output_path, "w") as GenFeatInput:
        GenFeatInput.write(
            str(config["Rc_M"])
            + ", "
            + str(config["maxNeighborNum"])
            + "             !  Rc_M, m_neigh \n"
        )
        
        atomTypeNum = len(config["atomType"])
        GenFeatInput.write(str(atomTypeNum) + "               ! ntype \n")
        for i in range(atomTypeNum):
            idAtomTypeConfig = config["atomType"][i]
            GenFeatInput.write(
                str(idAtomTypeConfig["type"]) + "              ! iat-type \n"
            )

            GenFeatInput.write(
                str(idAtomTypeConfig["Rc"])
                + ","
                + str(idAtomTypeConfig["Rm"])
                + ","
                + str(idAtomTypeConfig["iflag_grid"])
                + ","
                + str(idAtomTypeConfig["fact_base"])
                + ","
                + str(idAtomTypeConfig["dR1"])
                + "      !Rc,Rm,iflag_grid,fact_base,dR1 \n"
            )

        GenFeatInput.write(str(config["E_tolerance"]) + "    ! E_tolerance  \n")
        GenFeatInput.write(str(config["gen_egroup_input"]) + "    ! calculate Egroup if 1  \n")

    # output_path = os.path.join(config["dRFeatureInputDir"], "egroup.in")
    # with open(output_path, "w") as f:
    #     f.writelines(str(config["dwidth"]) + "\n")
    #     f.writelines(str(len(config["atomType"])) + "\n")
    #     for i in range(len(config["atomType"])):
    #         f.writelines(str(config["atomType"][i]["b_init"]) + "\n")

'''
description: 
write Ei.dat, the Ei is calculated by Ep
param {*} movement_files
param {*} train_set_dir "PWdata/"
return {*}
author: wuxingxing
'''
def set_Ei_dat_by_Ep(movement_files,train_set_dir):
    # make Ei label the Ep (one with minus sign)
    for mvm_index, movement_file in enumerate(movement_files):
        mvm_file = os.path.join(movement_file, "MOVEMENT")
        mvm = MOVEMENT(mvm_file)
        for k in range(0, mvm.image_nums):
            Ep = mvm.image_list[k].Ep
            atom_type_nums_list = mvm.image_list[k].atom_type_num
            print(atom_type_nums_list, Ep)
            tmp_Ep_shift, _, _, _ = np.linalg.lstsq([atom_type_nums_list], np.array([Ep]), rcond=1e-3)
            with open(os.path.join(train_set_dir, "Ei.dat"), "a") as Ei_out:
                for i in range(len(atom_type_nums_list)):
                    for j in range(atom_type_nums_list[i]):
                        Ei_out.write(str(tmp_Ep_shift[i]) + "\n")
********************************************* disuse **********************************"""    
def gen_train_data(train_ratio, raw_data_path, datasets_path,
                   train_data_path, valid_data_path, 
                   data_shuffle=True, seed=2024, format="pwmat/movement"):
    """
    Generate training data for MLFF model.

    Args:
        train_ratio (float): Ratio of training data to total data.
        raw_data_path (list): List of paths to raw data. MOVEMENT, OUTCAR, etc.
        datasets_path (str): Path to the directory containing the temp *.npy files.
        train_data_path (str): Path to the directory containing the training data.
        valid_data_path (str): Path to the directory containing the validation data.
        data_shuffle (bool, optional): Whether to shuffle the data. Defaults to True.
        seed (int, optional): Random seed for shuffling the data. Defaults to 2024.
        format (str, optional): Format of the raw data. Defaults to "movement".

    Returns:
        list: List of paths to the labels.
    """
    from pwdata import Save_Data
    labels_path = []
    for data_path in raw_data_path:
        data_name = os.path.basename(data_path)
        labels_path.append(os.path.join(datasets_path, data_name))
        Save_Data(data_path, datasets_path, train_data_path, valid_data_path, 
                    train_ratio, data_shuffle, seed, format)
    return labels_path

def get_stat(config, stat_add=None, datasets_path=None, work_dir=None):
    """
    Calculate statistical properties of the training data.

    Args:
        config (dict): Configuration parameters for the training data.
        stat_add (tuple, optional): Additional statistical properties. Defaults to None.
        datasets_path (list, optional): List of paths to data. Defaults to None.
        work_dir (str, optional): Path to working directory. Defaults to None.
        chunk_size (int, optional): Number of images each chunk. Defaults to 10.

    Returns:
        tuple: A tuple containing the average (davg) and standard deviation (dstd) of the pairwise distances,
               as well as the energy shift (energy_shift) and the maximum number of atoms in the movement (max_atom_nums).
    """
    train_data_path = config["trainDataPath"]
    ntypes = len(config["atomType"])
    input_atom_type = np.array([(_['type']) for _ in config["atomType"]])   # input atom type order
    davg_res = []
    dstd_res = []
    energy_res=[]
    energy_dict = {}
    for  _atom in input_atom_type:
        energy_dict[_atom] = []
    energy_dict['E'] = []
    if stat_add is not None:
        # load from prescribed path
        print("davg and dstd are from model checkpoint")
        davg_res, dstd_res, input_atom_type, energy_res = stat_add
        calculate_davg = False
    else:
        calculate_davg = True
    
    max_atom_nums = 0
    searched_atom = []
    for dataset_path in datasets_path:
        if os.path.exists(os.path.join(dataset_path, "image_type.npy")):
            atom_types_image_path = os.path.join(dataset_path, "image_type.npy")
            atom_type_path = os.path.join(dataset_path, "atom_type.npy")
            lattice_path = os.path.join(dataset_path, "lattice.npy")
            position_path = os.path.join(dataset_path, "position.npy")
            ei_path = os.path.join(dataset_path, "ei.npy")
            energy_path = os.path.join(dataset_path, "energies.npy")
        else:
            if not os.path.exists(os.path.join(dataset_path, train_data_path, "image_type.npy")):
                continue
            atom_types_image_path = os.path.join(dataset_path, train_data_path, "image_type.npy")
            atom_type_path = os.path.join(dataset_path, train_data_path, "atom_type.npy")
            lattice_path = os.path.join(dataset_path, train_data_path, "lattice.npy")
            position_path = os.path.join(dataset_path, train_data_path, "position.npy")
            energy_path = os.path.join(dataset_path, train_data_path, "energies.npy")
        atom_types_image = np.load(atom_types_image_path)
        max_atom_nums = max(max_atom_nums, atom_types_image.shape[1])
        if calculate_davg:
            cout_type, cout_num = np.unique(atom_types_image, return_counts=True)
            atom_types_image_dict = dict(zip(cout_type, cout_num))
            for element in input_atom_type:
                if element in list(atom_types_image_dict.keys()):
                    energy_dict[element].append(atom_types_image_dict[element])
                else:
                    energy_dict[element].append(0)
            _energy = np.load(energy_path)
            energy_dict['E'].append(np.mean(_energy[:min(_energy.shape[0], 10), :]))
            
            if len(searched_atom) == ntypes:
                continue
            _atom_types = np.load(atom_type_path)
            print(_atom_types.shape[1], atom_type_path)
            # if _atom_types.shape[1] != ntypes:
            #     continue
            # the davg and dstd only need calculate one time
            # the davg, dstd and energy_shift atom order are the same --> movement's atom order
            lattice = np.load(lattice_path)
            img_per_mvmt = lattice.shape[0]
            # if img_per_mvmt < chunk_size:
            #     continue
            chunk_size = min(img_per_mvmt, 10)
            position = np.load(position_path)
            # _Ei = np.load(ei_path)
            type_maps = np.array(type_map(atom_types_image[0], input_atom_type))
            _davg, _dstd, atom_types_nums = calculate_davg_dstd(config, lattice, position, chunk_size, _atom_types[0], input_atom_type, ntypes, type_maps)
            # _energy_shift = calculate_energy_shift(chunk_size, _Ei, atom_types_nums)
            for idx, _type in enumerate(_atom_types[0].tolist()):
                if _type not in searched_atom:
                    searched_atom.append(_type)
                    davg_res.append(np.tile(_davg[idx], config["maxNeighborNum"]*ntypes).reshape(-1,4))
                    dstd_res.append(np.tile(_dstd[idx], config["maxNeighborNum"]*ntypes).reshape(-1,4))
                    # energy_res.append(_energy_shift[idx])
    
    if calculate_davg:
        davg_res = np.array(davg_res).reshape(ntypes, -1)
        dstd_res = np.array(dstd_res).reshape(ntypes, -1)
        #calculate ei
        _num_matrix = []
        for key in energy_dict.keys():
            if key != 'E':
                _num_matrix.append(energy_dict[key])
        x, residuals, rank, s = np.linalg.lstsq(np.array(_num_matrix).T, energy_dict['E'], rcond=None)
        energy_res = x.tolist()
        davg_res, dstd_res = adjust_order_same_as_user_input(davg_res, dstd_res, searched_atom, input_atom_type)
    return davg_res, dstd_res, energy_res, max_atom_nums
    # if os.path.exists(os.path.join(work_dir, "davg.npy")) is False:
    #     np.save(os.path.join(work_dir, "davg.npy"), davg)
    #     np.save(os.path.join(work_dir, "dstd.npy"), dstd)
    #     np.save(os.path.join(work_dir, "energy_shift.npy"), energy_shift)
    #     np.save(os.path.join(work_dir, "max_atom_nums.npy"), max_atom_nums)

def type_map(atom_types_image, atom_type):
    """
    Maps the atom types to their corresponding indices in the atom_type array.

    Args:
    atom_types_image (numpy.ndarray): Array of atom types to be mapped.
    atom_type (numpy.ndarray): Array of integers representing the atom type of each atom in the system.

    Returns:
    list: List of indices corresponding to the atom types in the atom_type array.

    Raises:
    AssertionError: If no atom types in atom_types_image are found in atom_type.

    Examples: CH4 molecule
    >>> atom_types_image = array([6, 1, 1, 1, 1])
    >>> atom_type = array([6, 1])
    >>> type_map(atom_types_image, atom_type)
    [0, 1, 1, 1, 1]
    """
    atom_type_map = []
    for elem in atom_types_image:
        if elem in atom_type:
            atom_type_map.append(np.where(atom_type == elem)[0][0])
    assert len(atom_type_map) != 0, "this atom type didn't found"
    return atom_type_map

def calculate_davg_dstd(config, lattice, position, chunk_size, _atom_types, input_atom_type, ntypes, type_maps):
    """
    Calculate the average and standard deviation of the pairwise distances between atoms.

    neighconst is a fortran module, which is used to calculate the pairwise distances between atoms.

    Args:
        config (dict): Configuration parameters.
        lattice (ndarray): Lattice vectors.
        position (ndarray): Atomic positions.
        chunk_size (int): Number of images in each chunk.
        _atom_types (list): List of atom types in the movement.
        input_atom_type (ndarray): Atom types in the input file.
        ntypes (int): Number of atom types.
        type_maps (ndarray): Mapping of atom types.

    Returns:
        tuple: A tuple containing the average (davg) and standard deviation (dstd) of the pairwise distances,
               as well as the number of atoms for each atom type (atom_types_nums).
    """
    Rc_m = config["Rc_M"]
    m_neigh = config["maxNeighborNum"]
    # input_atom_type_nums = []       # the number of each atom type in input_atom_type
    # for itype, iatom in enumerate(input_atom_type):
    #     input_atom_type_nums.append(np.sum(itype == type_maps))
    types, type_incides, atom_types_nums = np.unique(type_maps, return_index=True, return_counts=True)
    atom_types_nums = atom_types_nums[np.argsort(type_incides)]
    Rc_type = np.asfortranarray(np.array([(_['Rc']) for _ in config["atomType"]]))
    type_maps = np.asfortranarray(type_maps + 1)
    lattice = np.asfortranarray(lattice[:chunk_size].reshape(chunk_size, 3, 3))
    position = np.asfortranarray(position[:chunk_size].reshape(chunk_size, -1, 3))
    natoms = position.shape[1]
    neighconst.find_neighbore(chunk_size, lattice, position, ntypes, natoms, m_neigh, Rc_m, Rc_type, type_maps)
    _list_neigh = neighconst.list_neigh
    _dR_neigh = neighconst.dr_neigh
    list_neigh = np.transpose(_list_neigh, (3, 2, 1, 0))
    dR_neigh = np.transpose(_dR_neigh, (4, 3, 2, 1, 0))
    atom_type_list = []
    for atom in list(_atom_types):
        atom_type_list.append(list(input_atom_type).index(atom))
    atom_type_list = sorted(atom_type_list)
    # dR_neigh = dR_neigh[:, :, atom_type_list, :,:]
    # list_neigh = list_neigh[:,:,atom_type_list,:]
    davg, dstd = calc_stat(config, np.copy(dR_neigh[:, :, atom_type_list, :,:]), np.copy(list_neigh[:,:,atom_type_list,:]), m_neigh, natoms, len(atom_type_list), atom_types_nums)
    neighconst.dealloc()
    return davg, dstd, atom_types_nums

def calc_stat(config, dR_neigh, list_neigh, m_neigh, natoms, ntypes, atom_types_nums):
    davg = []
    dstd = []
    image_dR = np.reshape(dR_neigh, (-1, natoms, ntypes * m_neigh, 3))
    list_neigh = np.reshape(list_neigh, (-1, natoms, ntypes * m_neigh))
    image_dR = torch.tensor(image_dR, dtype=torch.float64)
    list_neigh = torch.tensor(list_neigh, dtype=torch.int)

    mask = list_neigh > 0
    dR2 = torch.zeros_like(list_neigh, dtype=torch.float64)
    Rij = torch.zeros_like(list_neigh, dtype=torch.float64)
    dR2[mask] = torch.sum(image_dR[mask] * image_dR[mask], -1)
    Rij[mask] = torch.sqrt(dR2[mask])

    nr = torch.zeros_like(dR2)
    inr = torch.zeros_like(dR2)

    dR2_copy = dR2.unsqueeze(-1).repeat(1, 1, 1, 3)
    Ri_xyz = torch.zeros_like(dR2_copy)

    nr[mask] = dR2[mask] / Rij[mask]
    Ri_xyz[mask] = image_dR[mask] / dR2_copy[mask]
    inr[mask] = 1 / Rij[mask]

    davg_tensor = torch.zeros((ntypes, m_neigh * ntypes, 4), dtype=torch.float64)
    dstd_tensor = torch.ones((ntypes, m_neigh * ntypes, 4), dtype=torch.float64)
    Ri, _, _ = smooth(config, 
                      image_dR, 
                      nr, 
                      Ri_xyz, 
                      mask, 
                      inr, 
                      davg_tensor, 
                      dstd_tensor, 
                      atom_types_nums)
    Ri2 = Ri * Ri
    atom_sum = 0
    for i in range(ntypes):
        Ri_ntype = Ri[:, atom_sum : atom_sum + atom_types_nums[i]].reshape(-1, 4)
        Ri2_ntype = Ri2[:, atom_sum : atom_sum + atom_types_nums[i]].reshape(-1, 4)
        sum_Ri = Ri_ntype.sum(axis=0).tolist()
        sum_Ri_r = sum_Ri[0]
        sum_Ri_a = np.average(sum_Ri[1:])
        sum_Ri2 = Ri2_ntype.sum(axis=0).tolist()
        sum_Ri2_r = sum_Ri2[0]
        sum_Ri2_a = np.average(sum_Ri2[1:])
        sum_n = Ri_ntype.shape[0]

        davg_unit = [sum_Ri[0] / (sum_n + 1e-15), 0, 0, 0]
        dstd_unit = [
            compute_std(sum_Ri2_r, sum_Ri_r, sum_n),
            compute_std(sum_Ri2_a, sum_Ri_a, sum_n),
            compute_std(sum_Ri2_a, sum_Ri_a, sum_n),
            compute_std(sum_Ri2_a, sum_Ri_a, sum_n),
        ]
            
        # davg.append(
        #     np.tile(davg_unit, m_neigh * ntypes).reshape(-1, 4)
        # )
        # dstd.append(
        #     np.tile(dstd_unit, m_neigh * ntypes).reshape(-1, 4)
        # )
        davg.append(davg_unit)
        dstd.append(dstd_unit)

        atom_sum = atom_sum + atom_types_nums[i]

    # davg = np.array(davg).reshape(ntypes, -1)
    # dstd = np.array(dstd).reshape(ntypes, -1)
    return davg, dstd

def calculate_energy_shift(chunk_size, _Ei, atom_types_nums):
    Ei = _Ei[:chunk_size]
    res = []
    current_type = 0
    for atom_type_num in atom_types_nums:
        current_type_indices = current_type + atom_type_num
        avg_Ei = np.mean(Ei[:, current_type:current_type_indices])
        res.append(avg_Ei)
        current_type = current_type_indices
    return res
""" ********************************************* disuse **********************************
def gen_train_data(config, is_egroup = True, is_virial = True, alive_atomic_energy = True):

    trainset_dir = config["trainSetDir"]
    dRFeatureInputDir = config["dRFeatureInputDir"]
    dRFeatureOutputDir = config["dRFeatureOutputDir"]

    # directories that contain MOVEMENT 
    movement_files = collect_all_sourcefiles(trainset_dir, "MOVEMENT")

    #os.system("clean_data.sh")
    cmd_clear = "rm "+trainset_dir+"/*.dat"
    sp.run([cmd_clear],shell=True)
    
    if not os.path.exists(dRFeatureInputDir):
        os.mkdir(dRFeatureInputDir)

    if not os.path.exists(dRFeatureOutputDir):
        os.mkdir(dRFeatureOutputDir)

    gen_config_inputfile(config)

    for movement_file in movement_files:
        with open(os.path.join(movement_file, "MOVEMENT"), "r") as mov:
            lines = mov.readlines()
            etot_tmp = []
            for idx, line in enumerate(lines):
                
                if "Lattice vector" in line and "stress" in lines[idx + 1]:
                    # Virial.dat
                    if is_virial:
                        print (line)

                        tmp_v = []
                        cell = []
                        for dd in range(3):
                            tmp_l = lines[idx + 1 + dd]
                            cell.append([float(ss) for ss in tmp_l.split()[0:3]])
                            tmp_v.append([float(stress) for stress in tmp_l.split()[5:8]])

                        tmp_virial = np.zeros([3, 3])
                        tmp_virial[0][0] = tmp_v[0][0]
                        tmp_virial[0][1] = tmp_v[0][1]
                        tmp_virial[0][2] = tmp_v[0][2]
                        tmp_virial[1][0] = tmp_v[1][0]
                        tmp_virial[1][1] = tmp_v[1][1]
                        tmp_virial[1][2] = tmp_v[1][2]
                        tmp_virial[2][0] = tmp_v[2][0]
                        tmp_virial[2][1] = tmp_v[2][1]
                        tmp_virial[2][2] = tmp_v[2][2]
                        volume = np.linalg.det(np.array(cell))
                        print(volume)
                        print("====================================")
                        # import ipdb;ipdb.set_trace()
                        # tmp_virial = tmp_virial * 160.2 * 10.0 / volume
                        with open(
                            os.path.join(trainset_dir, "Virial.dat"), "a"
                        ) as virial_file:
                            virial_file.write(
                                str(tmp_virial[0, 0])
                                + " "
                                + str(tmp_virial[0, 1])
                                + " "
                                + str(tmp_virial[0, 2])
                                + " "
                                + str(tmp_virial[1, 0])
                                + " "
                                + str(tmp_virial[1, 1])
                                + " "
                                + str(tmp_virial[1, 2])
                                + " "
                                + str(tmp_virial[2, 0])
                                + " "
                                + str(tmp_virial[2, 1])
                                + " "
                                + str(tmp_virial[2, 2])
                                + "\n"
                            )
                
                elif "Lattice vector" in line and "stress" not in lines[idx + 1]:
                    if is_virial:
                        raise ValueError("Invalid input file: 'stress' is not present in the line.")
                    else:
                        Virial = None

                # Etot.dat
                if "Etot,Ep,Ek" in line:
                    etot_tmp.append(line.split()[9])

        with open(os.path.join(trainset_dir, "Etot.dat"), "a") as etot_file:
            for etot in etot_tmp:
                etot_file.write(etot + "\n")
    
    # ImgPerMVT  
    if alive_atomic_energy is False:
        set_Ei_dat_by_Ep(movement_files, config["trainSetDir"]) # set Ei.dat by Ep

    for movement_file in movement_files:
        tgt = os.path.join(movement_file, "MOVEMENT") 
        res = sp.check_output(["grep", "Iteration", tgt ,"-c"]) 
        
        with open(os.path.join(trainset_dir, "ImgPerMVT.dat"), "a") as ImgPerMVT:
            ImgPerMVT.write(str(int(res))+"\n")     

    location_path = os.path.join(config["dRFeatureInputDir"], "location")
    with open(location_path, "w") as location_writer:
        location_writer.write(str(len(movement_files)) + "\n")
        location_writer.write(os.path.abspath(trainset_dir) + "\n")

        for movement_path in movement_files:
            location_writer.write(movement_path + "\n")

    # if is_real_Ep is True:
    #     command = "gen_dR_nonEi.x | tee ./output/out"
    # else:
    command = "gen_dR.x | tee ./output/out"
    print("==============Start generating data==============")
    os.system(command)
    # command = "gen_egroup.x | tee ./output/out_write_egroup"
    # if is_egroup is True:
        # print("==============Start generating egroup==============")
        # os.system(command)
    
    print("==============Success==============")
    

def save_npy_files(data_path, data_set):
    print("Saving to ", data_path)
    print("    AtomType.npy", data_set["AtomType"].shape)
    np.save(os.path.join(data_path, "AtomType.npy"), data_set["AtomType"])
    print("    AtomTypeMap.npy", data_set["AtomTypeMap"].shape)
    np.save(os.path.join(data_path, "AtomTypeMap.npy"), data_set["AtomTypeMap"])
    print("    ImageDR.npy", data_set["ImageDR"].shape)
    np.save(os.path.join(data_path, "ImageDR.npy"), data_set["ImageDR"])
    print("    ListNeighbor.npy", data_set["ListNeighbor"].shape)
    np.save(os.path.join(data_path, "ListNeighbor.npy"), data_set["ListNeighbor"])
    # print("    NeighborType.npy", data_set["NeighborType"].shape)
    # np.save(os.path.join(data_path, "NeighborType.npy"), data_set["NeighborType"])
    print("    Ei.npy", data_set["Ei"].shape)
    np.save(os.path.join(data_path, "Ei.npy"), data_set["Ei"])
    
    if "Egroup" in data_set.keys():
        print("    Egroup.npy", data_set["Egroup"].shape)
        np.save(os.path.join(data_path, "Egroup.npy"), data_set["Egroup"])
    if "Divider" in data_set.keys():
        print("    Divider.npy", data_set["Divider"].shape)
        np.save(os.path.join(data_path, "Divider.npy"), data_set["Divider"])
    if "Egroup_weight" in data_set.keys():
        print("    Egroup_weight.npy", data_set["Egroup_weight"].shape)
        np.save(os.path.join(data_path, "Egroup_weight.npy"), data_set["Egroup_weight"])

    # print("    Ri.npy", data_set["Ri"].shape)
    # np.save(os.path.join(data_path, "Ri.npy"), data_set["Ri"])
    # print("    Ri_d.npy", data_set["Ri_d"].shape)
    # np.save(os.path.join(data_path, "Ri_d.npy"), data_set["Ri_d"])
    print("    Force.npy", data_set["Force"].shape)
    np.save(os.path.join(data_path, "Force.npy"), data_set["Force"])
    if "Virial" in data_set.keys():
        print("    Virial.npy", data_set["Virial"].shape)
        np.save(os.path.join(data_path, "Virial.npy"), data_set["Virial"])
    print("    Etot.npy", data_set["Etot"].shape)
    np.save(os.path.join(data_path, "Etot.npy"), data_set["Etot"])
    print("    ImageAtomNum.npy", data_set["ImageAtomNum"].shape)
    np.save(os.path.join(data_path, "ImageAtomNum.npy"), data_set["ImageAtomNum"])


'''
description: 
claculate davg and dstd, the atom type order is the same as movement  
param {*} config
param {*} image_dR
param {*} list_neigh
param {*} natoms_img
return {*}
author: wuxingxing
'''
def calc_stat(config, image_dR, list_neigh, natoms_img):

    davg = []
    dstd = []

    natoms_sum = natoms_img[0, 0]
    natoms_per_type = natoms_img[0, 1:]
    ntypes = len(natoms_per_type)

    image_dR = np.reshape(
        image_dR, (-1, natoms_sum, ntypes * config["maxNeighborNum"], 3)
    )
    list_neigh = np.reshape(
        list_neigh, (-1, natoms_sum, ntypes * config["maxNeighborNum"])
    )

    image_dR = torch.tensor(image_dR, dtype=torch.float64)
    list_neigh = torch.tensor(list_neigh, dtype=torch.int)

    # deepmd neighbor id 从 0 开始，MLFF从1开始
    mask = list_neigh > 0

    dR2 = torch.zeros_like(list_neigh, dtype=torch.float64)
    Rij = torch.zeros_like(list_neigh, dtype=torch.float64)
    dR2[mask] = torch.sum(image_dR[mask] * image_dR[mask], -1)
    Rij[mask] = torch.sqrt(dR2[mask])

    nr = torch.zeros_like(dR2)
    inr = torch.zeros_like(dR2)

    dR2_copy = dR2.unsqueeze(-1).repeat(1, 1, 1, 3)
    Ri_xyz = torch.zeros_like(dR2_copy)

    nr[mask] = dR2[mask] / Rij[mask]
    Ri_xyz[mask] = image_dR[mask] / dR2_copy[mask]
    inr[mask] = 1 / Rij[mask]

    davg_tensor = torch.zeros(
        (ntypes, config["maxNeighborNum"] * ntypes, 4), dtype=torch.float64
    )
    dstd_tensor = torch.ones(
        (ntypes, config["maxNeighborNum"] * ntypes, 4), dtype=torch.float64
    )
    Ri, _, _ = smooth(
        config,
        image_dR,
        nr,
        Ri_xyz,
        mask,
        inr,
        davg_tensor,
        dstd_tensor,
        natoms_per_type,
    )
    Ri2 = Ri * Ri

    atom_sum = 0

    for i in range(ntypes):
        Ri_ntype = Ri[:, atom_sum : atom_sum + natoms_per_type[i]].reshape(-1, 4)
        Ri2_ntype = Ri2[:, atom_sum : atom_sum + natoms_per_type[i]].reshape(-1, 4)
        sum_Ri = Ri_ntype.sum(axis=0).tolist()
        sum_Ri_r = sum_Ri[0]
        sum_Ri_a = np.average(sum_Ri[1:])
        sum_Ri2 = Ri2_ntype.sum(axis=0).tolist()
        sum_Ri2_r = sum_Ri2[0]
        sum_Ri2_a = np.average(sum_Ri2[1:])
        sum_n = Ri_ntype.shape[0]

        davg_unit = [sum_Ri[0] / (sum_n + 1e-15), 0, 0, 0]
        dstd_unit = [
            compute_std(sum_Ri2_r, sum_Ri_r, sum_n),
            compute_std(sum_Ri2_a, sum_Ri_a, sum_n),
            compute_std(sum_Ri2_a, sum_Ri_a, sum_n),
            compute_std(sum_Ri2_a, sum_Ri_a, sum_n),
        ]
            
        davg.append(
            np.tile(davg_unit, config["maxNeighborNum"] * ntypes).reshape(-1, 4)
        )
        dstd.append(
            np.tile(dstd_unit, config["maxNeighborNum"] * ntypes).reshape(-1, 4)
        )
        atom_sum = atom_sum + natoms_per_type[i]

    davg = np.array(davg).reshape(ntypes, -1)
    dstd = np.array(dstd).reshape(ntypes, -1)
    return davg, dstd
********************************************* disuse **********************************"""
def compute_std(sum2, sum, sumn):

    if sumn == 0:
        return 1e-2
    val = np.sqrt(sum2 / sumn - np.multiply(sum / sumn, sum / sumn))
    if np.abs(val) < 1e-2:
        val = 1e-2
    return val


def smooth(config, image_dR, x, Ri_xyz, mask, inr, davg, dstd, atom_types_nums):

    batch_size = image_dR.shape[0]
    ntypes = len(atom_types_nums)

    """
    inr2 = torch.zeros_like(inr)
    inr3 = torch.zeros_like(inr)
    inr4 = torch.zeros_like(inr)

    inr2[mask] = inr[mask] * inr[mask]
    inr4[mask] = inr2[mask] * inr2[mask]
    inr3[mask] = inr4[mask] * x[mask]
    """

    uu = torch.zeros_like(x)
    vv = torch.zeros_like(x)
    # dvv = torch.zeros_like(x)

    res = torch.zeros_like(x)

    # x < rcut_min vv = 1;
    mask_min = x < config["atomType"][0]["Rm"]
    mask_1 = mask & mask_min  # [2,108,100]
    vv[mask_1] = 1
    # dvv[mask_1] = 0

    # rcut_min< x < rcut_max;
    mask_max = x < config["atomType"][0]["Rc"]
    mask_2 = ~mask_min & mask_max & mask
    # uu = (xx - rmin) / (rmax - rmin);
    uu[mask_2] = (x[mask_2] - config["atomType"][0]["Rm"]) / (
        config["atomType"][0]["Rc"] - config["atomType"][0]["Rm"]
    )
    vv[mask_2] = (
        uu[mask_2]
        * uu[mask_2]
        * uu[mask_2]
        * (-6 * uu[mask_2] * uu[mask_2] + 15 * uu[mask_2] - 10)
        + 1
    )
    """
    du = 1.0 / (config["atomType"][0]["Rc"] - config["atomType"][0]["Rm"])
    # dd = ( 3 * uu*uu * (-6 * uu*uu + 15 * uu - 10) + uu*uu*uu * (-12 * uu + 15) ) * du;
    dvv[mask_2] = (
        3
        * uu[mask_2]
        * uu[mask_2]
        * (-6 * uu[mask_2] * uu[mask_2] + 15 * uu[mask_2] - 10)
        + uu[mask_2] * uu[mask_2] * uu[mask_2] * (-12 * uu[mask_2] + 15)
    ) * du
    """
    mask_3 = ~mask_max & mask
    vv[mask_3] = 0
    # dvv[mask_3] = 0

    res[mask] = 1.0 / x[mask]
    Ri = torch.cat((res.unsqueeze(-1), Ri_xyz), dim=-1)
    """
    Ri_d = torch.zeros_like(Ri).unsqueeze(-1).repeat(1, 1, 1, 1, 3)  # 2 108 100 4 3
    tmp = torch.zeros_like(x)

    # deriv of component 1/r
    tmp[mask] = (
        image_dR[:, :, :, 0][mask] * inr3[mask] * vv[mask]
        - Ri[:, :, :, 0][mask] * dvv[mask] * image_dR[:, :, :, 0][mask] * inr[mask]
    )
    Ri_d[:, :, :, 0, 0][mask] = tmp[mask]
    tmp[mask] = (
        image_dR[:, :, :, 1][mask] * inr3[mask] * vv[mask]
        - Ri[:, :, :, 0][mask] * dvv[mask] * image_dR[:, :, :, 1][mask] * inr[mask]
    )
    Ri_d[:, :, :, 0, 1][mask] = tmp[mask]
    tmp[mask] = (
        image_dR[:, :, :, 2][mask] * inr3[mask] * vv[mask]
        - Ri[:, :, :, 0][mask] * dvv[mask] * image_dR[:, :, :, 2][mask] * inr[mask]
    )
    Ri_d[:, :, :, 0, 2][mask] = tmp[mask]

    # deriv of component x/r
    tmp[mask] = (
        2 * image_dR[:, :, :, 0][mask] * image_dR[:, :, :, 0][mask] * inr4[mask]
        - inr2[mask]
    ) * vv[mask] - Ri[:, :, :, 1][mask] * dvv[mask] * image_dR[:, :, :, 0][mask] * inr[
        mask
    ]
    Ri_d[:, :, :, 1, 0][mask] = tmp[mask]
    tmp[mask] = (
        2 * image_dR[:, :, :, 0][mask] * image_dR[:, :, :, 1][mask] * inr4[mask]
    ) * vv[mask] - Ri[:, :, :, 1][mask] * dvv[mask] * image_dR[:, :, :, 1][mask] * inr[
        mask
    ]
    Ri_d[:, :, :, 1, 1][mask] = tmp[mask]
    tmp[mask] = (
        2 * image_dR[:, :, :, 0][mask] * image_dR[:, :, :, 2][mask] * inr4[mask]
    ) * vv[mask] - Ri[:, :, :, 1][mask] * dvv[mask] * image_dR[:, :, :, 2][mask] * inr[
        mask
    ]
    Ri_d[:, :, :, 1, 2][mask] = tmp[mask]

    # deriv of component y/r
    tmp[mask] = (
        2 * image_dR[:, :, :, 1][mask] * image_dR[:, :, :, 0][mask] * inr4[mask]
    ) * vv[mask] - Ri[:, :, :, 2][mask] * dvv[mask] * image_dR[:, :, :, 0][mask] * inr[
        mask
    ]
    Ri_d[:, :, :, 2, 0][mask] = tmp[mask]
    tmp[mask] = (
        2 * image_dR[:, :, :, 1][mask] * image_dR[:, :, :, 1][mask] * inr4[mask]
        - inr2[mask]
    ) * vv[mask] - Ri[:, :, :, 2][mask] * dvv[mask] * image_dR[:, :, :, 1][mask] * inr[
        mask
    ]
    Ri_d[:, :, :, 2, 1][mask] = tmp[mask]
    tmp[mask] = (
        2 * image_dR[:, :, :, 1][mask] * image_dR[:, :, :, 2][mask] * inr4[mask]
    ) * vv[mask] - Ri[:, :, :, 2][mask] * dvv[mask] * image_dR[:, :, :, 2][mask] * inr[
        mask
    ]
    Ri_d[:, :, :, 2, 2][mask] = tmp[mask]

    # deriv of component z/r
    tmp[mask] = (
        2 * image_dR[:, :, :, 2][mask] * image_dR[:, :, :, 0][mask] * inr4[mask]
    ) * vv[mask] - Ri[:, :, :, 3][mask] * dvv[mask] * image_dR[:, :, :, 0][mask] * inr[
        mask
    ]
    Ri_d[:, :, :, 3, 0][mask] = tmp[mask]
    tmp[mask] = (
        2 * image_dR[:, :, :, 2][mask] * image_dR[:, :, :, 1][mask] * inr4[mask]
    ) * vv[mask] - Ri[:, :, :, 3][mask] * dvv[mask] * image_dR[:, :, :, 1][mask] * inr[
        mask
    ]
    Ri_d[:, :, :, 3, 1][mask] = tmp[mask]
    tmp[mask] = (
        2 * image_dR[:, :, :, 2][mask] * image_dR[:, :, :, 2][mask] * inr4[mask]
        - inr2[mask]
    ) * vv[mask] - Ri[:, :, :, 3][mask] * dvv[mask] * image_dR[:, :, :, 2][mask] * inr[
        mask
    ]
    Ri_d[:, :, :, 3, 2][mask] = tmp[mask]
    """
    vv_copy = vv.unsqueeze(-1).repeat(1, 1, 1, 4)
    Ri[mask] *= vv_copy[mask]

    davg_res, dstd_res = None, None
    # 0 is that the atom nums is zero, for example, CH4 system in CHO system hybrid training, O atom nums is zero.\
    # beacuse the dstd or davg does not contain O atom, therefore, special treatment is needed here for atoms with 0 elements
    # atom_types_nums = [_ for _ in atom_types_nums if _ != 0]
    # ntypes = len(atom_types_nums)
    for ntype in range(ntypes):
        atom_num_ntype = atom_types_nums[ntype]
        davg_ntype = (
            davg[ntype].reshape(-1, 4).repeat(batch_size, atom_num_ntype, 1, 1)
        )  # [32,100,4]
        dstd_ntype = (
            dstd[ntype].reshape(-1, 4).repeat(batch_size, atom_num_ntype, 1, 1)
        )  # [32,100,4]
        davg_res = davg_ntype if davg_res is None else torch.concat((davg_res, davg_ntype), dim=1)
        dstd_res = dstd_ntype if dstd_res is None else torch.concat((dstd_res, dstd_ntype), dim=1)

    max_ri = torch.max(Ri[:,:,:,0])
    Ri = (Ri - davg_res) / dstd_res
    # dstd_res = dstd_res.unsqueeze(-1).repeat(1, 1, 1, 1, 3)
    # Ri_d = Ri_d / dstd_res
    return Ri, None, max_ri

""" ********************************************* disuse **********************************
def compute_Ri(config, image_dR, list_neigh, natoms_img, ind_img, davg, dstd):
    natoms_sum = natoms_img[0, 0]
    natoms_per_type = natoms_img[0, 1:]
    ntypes = len(natoms_per_type)
    max_ri_list = [] # max Rij before davg and dstd cacled
    #if torch.cuda.is_available():
    #    device = torch.device("cuda")
    #else:
    
    device = torch.device("cpu")

    davg = torch.tensor(np.array(davg), device=device, dtype=torch.float64)
    dstd = torch.tensor(np.array(dstd), device=device, dtype=torch.float64)

    image_num = natoms_img.shape[0]

    img_seq = [0]
    seq_len = 0
    tmp_img = natoms_img[0]
    for i in range(image_num):
        if (natoms_img[i] != tmp_img).sum() > 0 or seq_len >= 500:
            img_seq.append(i)
            seq_len = 1
            tmp_img = natoms_img[i]
        else:
            seq_len += 1

    if img_seq[-1] != image_num:
        img_seq.append(image_num)

    for i in range(len(img_seq) - 1):
        start_index = img_seq[i]
        end_index = img_seq[i + 1]

        natoms_sum = natoms_img[start_index, 0]
        natoms_per_type = natoms_img[start_index, 1:]
       
        image_dR_i = image_dR[
            ind_img[start_index]
            * config["maxNeighborNum"]
            * ntypes : ind_img[end_index]
            * config["maxNeighborNum"]
            * ntypes
        ]
        list_neigh_i = list_neigh[
            ind_img[start_index]
            * config["maxNeighborNum"]
            * ntypes : ind_img[end_index]
            * config["maxNeighborNum"]
            * ntypes
        ]

        image_dR_i = np.reshape(
            image_dR_i, (-1, natoms_sum, ntypes * config["maxNeighborNum"], 3)
        )
        list_neigh_i = np.reshape(
            list_neigh_i, (-1, natoms_sum, ntypes * config["maxNeighborNum"])
        )

        image_dR_i = torch.tensor(image_dR_i, device=device, dtype=torch.float64)
        list_neigh_i = torch.tensor(list_neigh_i, device=device, dtype=torch.int)

        # deepmd neighbor id 从 0 开始，MLFF从1开始
        mask = list_neigh_i > 0 # 0 means the centor atom i does not have neighor

        dR2 = torch.zeros_like(list_neigh_i, dtype=torch.float64)
        Rij_temp = torch.zeros_like(list_neigh_i, dtype=torch.float64)
        dR2[mask] = torch.sum(image_dR_i[mask] * image_dR_i[mask], -1)
        Rij_temp[mask] = torch.sqrt(dR2[mask])

        nr = torch.zeros_like(dR2)
        inr = torch.zeros_like(dR2)

        dR2_copy = dR2.unsqueeze(-1).repeat(1, 1, 1, 3)
        Ri_xyz = torch.zeros_like(dR2_copy)

        nr[mask] = dR2[mask] / Rij_temp[mask]
        Ri_xyz[mask] = image_dR_i[mask] / dR2_copy[mask]
        inr[mask] = 1 / Rij_temp[mask]

        Ri_i, Ri_d_i, max_ri = smooth(
            config, image_dR_i, nr, Ri_xyz, mask, inr, davg, dstd, natoms_per_type
        )

        # Ri_i = Ri_i.reshape(-1, ntypes * config["maxNeighborNum"], 4)
        # Ri_d_i = Ri_d_i.reshape(-1, ntypes * config["maxNeighborNum"], 4, 3)
        Rij_temp = Rij_temp.reshape(-1, ntypes * config["maxNeighborNum"]).unsqueeze(-1)

        if i == 0:
            # Ri = Ri_i.detach().cpu().numpy()
            # Ri_d = Ri_d_i.detach().cpu().numpy()
            Rij = Rij_temp.detach().cpu().numpy()
        else:
            # Ri_i = Ri_i.detach().cpu().numpy()
            # Ri_d_i = Ri_d_i.detach().cpu().numpy()
            Rij_temp = Rij_temp.detach().cpu().numpy()
            # Ri = np.concatenate((Ri, Ri_i), 0)
            # Ri_d = np.concatenate((Ri_d, Ri_d_i), 0)
            Rij = np.concatenate((Rij, Rij_temp), 0)
        max_ri_list.append(max_ri)

    if config['gen_egroup_input'] == 1:
        dwidth = np.sqrt(-config['atomType'][0]['Rc']**2 / np.log(0.01))
        egroup_weight_neigh = torch.exp(-dR2[mask] / dwidth / dwidth).to(device)
        egroup_weight_neigh = torch.reshape(egroup_weight_neigh, (-1, natoms_sum, natoms_sum - 1))
        egroup_weight_expanded = torch.zeros(size=(egroup_weight_neigh.shape[0], natoms_sum, natoms_sum), dtype=torch.float64)
        egroup_weight_low_diag = torch.tril(egroup_weight_neigh, diagonal=-1)
        egroup_weight_expanded[:, :natoms_sum, :egroup_weight_neigh.shape[2]] = egroup_weight_low_diag
        egroup_weight_all = egroup_weight_expanded + egroup_weight_expanded.transpose(-1,-2)
        for image in range(egroup_weight_neigh.shape[0]):
            egroup_weight_all[image].diagonal().fill_(1)   
                
        divider = egroup_weight_all.sum(-1)

        egroup_weight_all = egroup_weight_all.detach().cpu().numpy().reshape(-1, natoms_sum)
        divider = divider.detach().cpu().numpy().reshape(-1)
    else:
        egroup_weight_all = None
        divider = None

    return None, None, egroup_weight_all, divider, max(max_ri_list), Rij

'''
description:
    classify movements according to thier atomtypes
    example: for systems: movement1[C,H,O], movement2[C,H], movement3[H,C,O], movement4[C], movement5[C,H,O]
                after classify:
                    movement1[C,H,O], movement5[C,H,O] belong to the same system.
                    movement2[C,H], movement3[H,C,O],movement4[C] are different system.
                    The atomic order of movement3[H,C,O] and movement5[C,H,O] is different, so they are different system.
param {*} img_per_mvmt
param {*} atom_num_per_image
param {*} atom_types
param {*} max_neighbor_num
param {*} ntypes the input of user
return {*}
author: wuxingxing
'''
def _classify_systems(img_per_mvmt, atom_num_per_image, atom_types, max_neighbor_num, ntypes):
    # read loactions of movement ?
    # for each movement, get the first image and count its atom type info
    movement_info = {}
    dr_start = 0
    for idx_mvmt, imgs_mvmt in enumerate(img_per_mvmt):
        idx_img = sum(img_per_mvmt[:idx_mvmt])
        img_atom_nums = atom_num_per_image[idx_img]
        # atom start index in AtomType.dat
        idx_atom_start_img = sum(atom_num_per_image[:sum(img_per_mvmt[:idx_mvmt])])
        atom_list = atom_types[idx_atom_start_img: idx_atom_start_img + img_atom_nums]
        types, type_nums, key = _get_type_info(atom_list)
        # Key consists of atomic type (atomic order is in the order of movement) and atomic number.
        movement_info[idx_mvmt] = {"image_nums":imgs_mvmt, 
            "atom_nums":sum(atom_num_per_image[idx_img:idx_img + imgs_mvmt]),
                "types":types, "type_nums":type_nums, "key":key}
        
        # get dRneigh indexs of the movement in the dRneigh.dat file
        # num of dRneigh = img_nums * atom_nums * all_atom_types * max nerghbor nums
        # all_atom_types and max nerghbor nums are global variables
        dr_rows = imgs_mvmt * sum(type_nums) * ntypes * max_neighbor_num 
        movement_info[idx_mvmt]["drneigh_rows"] = [dr_start, dr_start + dr_rows]
        dr_start += dr_rows
        # get Etot indexs of the movement in the Etot.dat file
        movement_info[idx_mvmt]["etot_rows"] = [idx_img, idx_img+imgs_mvmt]
        # get Ei index of the movement in the Ei.dat file
        movement_info[idx_mvmt]["ei_rows"] = [idx_atom_start_img, idx_atom_start_img + imgs_mvmt*img_atom_nums]
        # get Force index of the movement in the Force.dat file
        movement_info[idx_mvmt]["force_rows"] = movement_info[idx_mvmt]["ei_rows"]
        # the index of movement in input/local file
        movement_info[idx_mvmt]["mvm_index"] = idx_mvmt
        # set egroup and viral
        
    # The movement is sorted according to the number of atomic types. \
    # After that, the first MOVEMENT in movement_info dict has all atomic types, and will be used to calculate davg, dstd and energy_shift
    movement_info = sorted(movement_info.items(), key = lambda x: len(x[1]['types']), reverse=True)

    # assert len(movement_info[0][1]['types'])== ntypes, "Error: At least one input movement should contain all atomic types!"
    # classfiy movement_info by key
    classify = {}
    for mvm in movement_info:
        mvm = mvm[1] # mvm format is:(0, {'image_nums': 100, 'atom_nums': 1000, 'types': [...], 'type_nums': [...], 'key': '8_6_1_10', ...})
        if mvm['key'] not in classify.keys():
            classify[mvm['key']] = [mvm]
        else:
            classify[mvm['key']].append(mvm)      
    return classify

'''
description: 
    count atom type and atom numbers of each type, \
        key consists of atomic type (atomic order is in the order of movement) and atomic number.
param {*} atom_list the atom list of one image
    such as a Li-Si image: [3,3,3,3,3,14,14,14,14,14,14,14]
return {*}  types, the nums of type, and key
    such as [3, 14], [5, 7], "3_14_5_7"
author: wuxingxing
'''
def _get_type_info(atom_list: list):
    types = {}
    for atom in atom_list:
        if atom in types.keys():
            types[atom] += 1
        else:
            types[atom] = 1
    key = ""
    for k in types.keys():
        key += "{}_".format(k)
    key += "{}".format(len(atom_list))
    
    type_list = list(types.keys())
    type_list_nums = list(types.values())
    key1 = "_".join(str(item) for item in type_list)
    key2 = '_'.join(str(item) for item in type_list_nums)
    key = "{}_{}".format(key1, key2)
    return type_list, type_list_nums, key

'''
description:
    sepper .dat data to npy format:
    For hybrid data, there are many different systems, which contain different atomic numbers and different atomic types.
        1. classify movements according to thier atomtypes and atom numbers.
        2. calculate davg, dstd and energy_shift from system which contain all atom types.
        3. for movements in the same category, call function sepper_data.
        4. the last, save davg, dstd and energy_shift.
    
    Srij_max is the max S(rij) before doing scaled by dstd and davg, this value is used for model compress
param {*} config
param {*} is_egroup
param {*} is_load_stat
param {*} stat_add
return {*}
author: wuxingxing
'''
def sepper_data_main(config, is_egroup = True, stat_add = None, valid_random=False, seed=None): 
    trainset_dir = config["trainSetDir"]
    train_data_path = config["trainDataPath"] 
    valid_data_path = config["validDataPath"]
    max_neighbor_num = config["maxNeighborNum"]
    # directories that contain MOVEMENT 
    # _movement_files = np.loadtxt(os.path.join(config["dRFeatureInputDir"], "location"), dtype=str)[2:].tolist()
    ntypes = len(config["atomType"])
    atom_type_list = [int(_['type']) for _ in config["atomType"]] # get atom types,the order is consistent with user input order
    # image number in each movement 
    img_per_mvmt = np.loadtxt(os.path.join(trainset_dir, "ImgPerMVT.dat"), dtype=int)
    # when there is only one movement, convert img_per_mvmt type: array(num) -> [array(num)]
    if img_per_mvmt.size == 1:
        img_per_mvmt = [img_per_mvmt]
    # atom nums in each image
    atom_num_per_image = np.loadtxt(os.path.join(trainset_dir, "ImageAtomNum.dat"), dtype=int)    
    # atom type of each atom in the image
    atom_types = np.loadtxt(os.path.join(trainset_dir, "AtomType.dat"), dtype=int) 
    movement_classify = _classify_systems(img_per_mvmt, atom_num_per_image, atom_types, max_neighbor_num, ntypes)
       
    dR_neigh = np.loadtxt(os.path.join(trainset_dir, "dRneigh.dat"))
    Etot = np.loadtxt(os.path.join(trainset_dir, "Etot.dat"))
    Ei = np.loadtxt(os.path.join(trainset_dir, "Ei.dat"))
    Force = np.loadtxt(os.path.join(trainset_dir, "Force.dat"))
    if is_egroup:
        Egroup  = np.loadtxt(os.path.join(trainset_dir, "Egroup.dat"), delimiter=",", usecols=0)   
        # divider = np.loadtxt(os.path.join(trainset_dir, "Egroup_weight.dat"), delimiter=",", usecols=1)   
        # take care of weights
        # fp = open(os.path.join(trainset_dir, "Egroup_weight.dat"),"r")
        # raw_egroup = fp.readlines()
        # fp.close()
        # form a list to contain 1-d np arrays 
        # egroup_single_arr = []  
        # for line in raw_egroup:
        #     tmp  = [float(item) for item in line.split(",")]
        #     tmp  = tmp[2:]
        #     egroup_single_arr.append(np.array(tmp))
    else:
        # Egroup, divider, egroup_single_arr = None, None, None
        Egroup = None

    if os.path.exists(os.path.join(trainset_dir, "Virial.dat")):
        Virial = np.loadtxt(os.path.join(trainset_dir, "Virial.dat"), delimiter=" ")
    else:
        Virial = None

    if stat_add is not None:
        # load from prescribed path
        print("davg and dstd are from model checkpoint")
        davg, dstd, atom_type_order, energy_shift = stat_add
        # if energy_shift.size == 1: #
        #     energy_shift = [energy_shift]
    else:
        # calculate davg and dstd from first category of movement_classify
        davg, dstd = None, None
    Srij_max = 0.0
    img_start = [0, 0] # the index of images saved (train set and valid set)
    for mvm_type_key in movement_classify.keys():

        # _Egroup, _divider, _egroup_single_arr, _Virial = None, None, None, None
        #construct data
        for mvm in movement_classify[mvm_type_key]:
            _Etot, _Ei, _Force, _dR = None, None, None, None
            _atom_num_per_image, _atom_types, _img_per_mvmt = None, None, None,
            _Egroup, _Virial = None, None

            _Etot = Etot[mvm["etot_rows"][0]:mvm["etot_rows"][1]]
            _Ei = Ei[mvm["ei_rows"][0]:mvm["ei_rows"][1]]
            _Force = Force[mvm["force_rows"][0]:mvm["force_rows"][1]]
            _dR = dR_neigh[mvm["drneigh_rows"][0]:mvm["drneigh_rows"][1]]
            # egroup
            if Egroup is not None:
                _Egroup = Egroup[mvm["ei_rows"][0]:mvm["ei_rows"][1]]
                # _divider = divider[mvm["ei_rows"][0]:mvm["ei_rows"][1]] if _divider is None \
                #     else np.concatenate([_divider, divider[mvm["ei_rows"][0]:mvm["ei_rows"][1]]],axis=0)
                # _egroup_single_arr = egroup_single_arr[mvm["ei_rows"][0]:mvm["ei_rows"][1]] if _egroup_single_arr is None \
                #     else np.concatenate([_egroup_single_arr, egroup_single_arr[mvm["ei_rows"][0]:mvm["ei_rows"][1]]],axis=0)
            # Virial not realized
            if Virial is not None:
                _Virial = Virial[mvm["etot_rows"][0]:mvm["etot_rows"][1]]

            _atom_num_per_image = atom_num_per_image[mvm["etot_rows"][0]:mvm["etot_rows"][1]]
            _atom_types = atom_types[mvm["ei_rows"][0]:mvm["ei_rows"][1]]
            _img_per_mvmt = [img_per_mvmt[mvm["mvm_index"]]]

            if davg is None:
                # the davg and dstd only need calculate one time
                # the davg, dstd and energy_shift atom order are the same --> atom_type_order 
                davg, dstd = _calculate_davg_dstd(config, _dR, _atom_types, _atom_num_per_image)
                energy_shift, atom_type_order = _calculate_energy_shift(_Ei, _atom_types, _atom_num_per_image)
                davg, dstd, energy_shift, atom_type_order = adjust_order_same_as_user_input(davg, dstd, energy_shift,atom_type_order, atom_type_list)
            # reorder davg and dstd to consistent with atom type order of current movement
            _davg, _dstd = _reorder_davg_dstd(davg, dstd, list(atom_type_order), mvm['types'])

            accum_train_num, accum_valid_num, _Srij_max = sepper_data(config, _Etot, _Ei, _Force, _dR, \
                                                      _atom_num_per_image, _atom_types, _img_per_mvmt, \
                                                      _Egroup, _Virial, \
                                                      _davg, _dstd,\
                                                      stat_add, img_start, valid_random, seed)
            Srij_max = max(_Srij_max, Srij_max)
            img_start = [accum_train_num, accum_valid_num]

    if os.path.exists(os.path.join(train_data_path, "davg.npy")) is False:
        np.save(os.path.join(train_data_path, "davg.npy"), davg)
        np.save(os.path.join(valid_data_path, "davg.npy"), davg)
        np.save(os.path.join(train_data_path, "dstd.npy"), dstd)
        np.save(os.path.join(valid_data_path, "dstd.npy"), dstd)
        np.savetxt(os.path.join(train_data_path, "atom_map.raw"), atom_type_order, fmt="%d")
        np.savetxt(os.path.join(valid_data_path, "atom_map.raw"), atom_type_order, fmt="%d")
        np.savetxt(os.path.join(train_data_path, "energy_shift.raw"), energy_shift)
        np.savetxt(os.path.join(valid_data_path, "energy_shift.raw"), energy_shift)
        np.savetxt(os.path.join(train_data_path, "sij_max.raw"), [Srij_max], fmt="%.6f")
        np.savetxt(os.path.join(valid_data_path, "sij_max.raw"), [Srij_max], fmt="%.6f")
                

'''
description: 
According to the atom type and order of tar_order output corresponding davg and dstd
    example
         for source order O-C-H system: davg[0] is O atom, davg[1] is C atom, and davg[2] is H atom:
                for a target order H-C-O system: davg[0] is H atom, davg[1] is C atom, and davg[2] is O atom
                for a target order H-C system: davg[0] is H atom, davg[1] is C atom.
        dstd is same as above.
param {*} davg
param {*} dstd
param {*} sor_order the input order of davg and dstd
param {*} tar_order the output order of davg and dstd
return {*}
author: wuxingxing
'''
def _reorder_davg_dstd(davg, dstd, sor_order, tar_order):
    tar_davg, tar_dstd = [], []
    for i in tar_order:
        tar_davg.append(davg[sor_order.index(i)])
        tar_dstd.append(dstd[sor_order.index(i)])
    return tar_davg, tar_dstd

'''
description: 
    calculate energy shift, this value is used in DP model when doning the fitting net bias_init
    energy shift is the avrage value of atom's Ei. 
param {*} Ei
param {*} atom_type
param {*} atom_num_per_image 
param {*} chunk_size: the image nums for energy shift calculating
return: two list: energy shift list and atom type list
        example: for a li-si system: [-191.614604541, -116.03510427249998], [3, 14]
author: wuxingxing
'''
def _calculate_energy_shift(Ei, atom_type, atom_num_per_image,  chunk_size=10):
    if chunk_size > len(atom_num_per_image):
        chunk_size = len(atom_num_per_image)
    Ei = Ei[: sum(atom_num_per_image[:chunk_size])]
    atom_type = atom_type[: sum(atom_num_per_image[:chunk_size])]
    type_dict = {}
    for i in range(sum(atom_num_per_image[:chunk_size])):
        if atom_type[i] not in type_dict.keys():
            type_dict[atom_type[i]] = [Ei[i]]
        else:
            type_dict[atom_type[i]].append(Ei[i])
    res = []
    for t in type_dict.keys():
        res.append(np.mean(type_dict[t]))
    return res, list(type_dict.keys())
********************************************* disuse **********************************"""
'''
description: 
adjust atom ordor of davg, dstd, energy_shift to same as user input order
param {list} davg
param {list} dstd
param {list} atom_type_order: the input davg, dstd atom order
param {list} atom_type_list: the user input order 
return {*}
author: wuxingxing
'''
def adjust_order_same_as_user_input(davg:list, dstd:list, atom_type_order:list, atom_type_list:list):
    davg_res, dstd_res = [], []
    for i, atom in enumerate(atom_type_list):
        davg_res.append(davg[atom_type_order.index(atom)])
        dstd_res.append(dstd[atom_type_order.index(atom)])
        # energy_shift_res.append(energy_shift[atom_type_order.index(atom)])
    return davg_res, dstd_res
""" ********************************************* disuse **********************************        
'''
description: 
    calculate davg and dstd, the atom type order of davg and dstd is same as input paramter atom_type 
param {*} config
param {*} dR_neigh
param {*} atom_type, atom list in image, such as a li-si system: atom_type = [3,3,3,3,3,3,3,14,14,14,14,14] 
param {*} chunk_size, chose 10(default) images.
return {*}
author: wuxingxing
'''
def _calculate_davg_dstd(config, dR_neigh, atom_type, atom_num_per_image, chunk_size=10):
    ntypes = len(config["atomType"])
    max_neighbor_num = config["maxNeighborNum"]
    
    image_dR = dR_neigh[:, :3]
    list_neigh = dR_neigh[:, 3]
    
    image_index = np.insert(
        atom_num_per_image, 0, 0
    ).cumsum()  # array([  0, 108, 216, 324, 432, 540, 648, 756, 864, 972])
    
    image_num = atom_num_per_image.shape[0]
    
    diff_atom_types_num = []
    for i in range(image_num):
        atom_type_per_image = atom_type[image_index[i] : image_index[i + 1]]
        ######## mask need to flexibly change according to atom_type
        # unique_values, indices = np.unique(atom_type_per_image, return_index=True)
        # mask = unique_values[np.argsort(indices)]
        mask = np.array([atom_type['type'] for atom_type in config["atomType"]])
        #######
        diff_atom_types_num.append(
            [Counter(atom_type_per_image)[mask[type]] for type in range(mask.shape[0])]
        )
    narray_diff_atom_types_num = np.array(diff_atom_types_num)
    atom_num_per_image = np.concatenate(
        (atom_num_per_image.reshape(-1, 1), narray_diff_atom_types_num), axis=1
    )
    if len(image_index)-1 < chunk_size:
        chunk_size = len(image_index)-1
    davg, dstd = calc_stat(
            config,
            image_dR[0 : image_index[chunk_size] * max_neighbor_num * ntypes],
            list_neigh[0 : image_index[chunk_size] * max_neighbor_num * ntypes],
            atom_num_per_image[0:chunk_size],
        )

    return davg, dstd
    
def sepper_data(config, Etot, Ei, Force, dR_neigh,\
                atom_num_per_image, atom_type, img_per_mvmt, \
                Egroup=None, Virial=None, \
                davg=None, dstd=None,\
                stat_add = "./", img_start=[0, 0], valid_random=False, seed=None):

    train_data_path = config["trainDataPath"]
    valid_data_path = config["validDataPath"]
    max_neighbor_num = config["maxNeighborNum"]
    ntypes = len(config["atomType"])
    
    image_dR = dR_neigh[:, :3]
    list_neigh = dR_neigh[:, 3]
    # neigh_type = dR_neigh[:, 4]
    
    image_index = np.insert(
        atom_num_per_image, 0, 0
    ).cumsum()  # array([  0, 108, 216, 324, 432, 540, 648, 756, 864, 972])
    
    mask = np.array([atom_type['type'] for atom_type in config["atomType"]])
    atom_type_map = np.array([np.argwhere(mask == atom)[0][0] for atom in atom_type])
    image_num = atom_num_per_image.shape[0]
    
    diff_atom_types_num = []
    for i in range(image_num):
        atom_type_per_image = atom_type[image_index[i] : image_index[i + 1]]
        ######## mask need to flexibly change according to atom_type
        # unique_values, indices = np.unique(atom_type_per_image, return_index=True)
        # mask = unique_values[np.argsort(indices)]
        #######
        diff_atom_types_num.append(
            [Counter(atom_type_per_image)[mask[type]] for type in range(mask.shape[0])]
        )
    narray_diff_atom_types_num = np.array(diff_atom_types_num)
    atom_num_per_image = np.concatenate(
        (atom_num_per_image.reshape(-1, 1), narray_diff_atom_types_num), axis=1
    )
    
    Ri, Ri_d, Egroup_weight, Divider, max_ri, Rij = compute_Ri( 
            config, image_dR, list_neigh, atom_num_per_image, image_index, davg, dstd
        )
    if not os.path.exists(train_data_path):
        os.makedirs(train_data_path)

    if not os.path.exists(valid_data_path):
        os.makedirs(valid_data_path)
    
    list_neigh = list_neigh.reshape(-1, max_neighbor_num * ntypes)
    # neigh_type = neigh_type.reshape(-1, max_neighbor_num * ntypes)
    image_dR = image_dR.reshape(-1, max_neighbor_num * ntypes, 3)
    image_dR = np.concatenate((Rij, image_dR), axis=-1)

    accum_train_num = img_start[0] 
    accum_valid_num = img_start[1]
    # width = len(str(accum_train_num))

    train_indexs, valid_indexs = random_index(image_num, config["ratio"], valid_random, seed)

    # index = 0
    for index in train_indexs:
        start_index = index
        end_index = index+1
        # end_index = min(end_index, len(train_indexs))
        train_set = {
                "AtomType": atom_type[image_index[start_index] : image_index[end_index]],
                "AtomTypeMap": atom_type_map[image_index[start_index] : image_index[end_index]],
                "ImageDR": image_dR[image_index[start_index] : image_index[end_index]],
                "ListNeighbor": list_neigh[image_index[start_index] : image_index[end_index]],
                # "NeighborType": neigh_type[image_index[start_index] : image_index[end_index]],
                "Ei": Ei[image_index[start_index] : image_index[end_index]],
                # "Ri": Ri[image_index[start_index] : image_index[end_index]],
                # "Ri_d": Ri_d[image_index[start_index] : image_index[end_index]],
                "Force": Force[image_index[start_index] : image_index[end_index]],
                "Etot": Etot[start_index:end_index],
                "ImageAtomNum": atom_num_per_image[start_index:end_index],
            }
        
        if Egroup is not None:
            train_set["Egroup"] = Egroup[image_index[start_index] : image_index[end_index]]
            # train_set["Divider"] = divider[image_index[start_index] : image_index[end_index]]
            train_set["Divider"] = Divider[image_index[start_index] : image_index[end_index]]
            # train_set["Egroup_weight"] = np.vstack(tuple(egroup_single_arr[image_index[start_index] : image_index[end_index]]))
            train_set["Egroup_weight"] = Egroup_weight[image_index[start_index] : image_index[end_index]]
        if Virial is not None:
            train_set["Virial"] = Virial[start_index:end_index]

        save_path = os.path.join(train_data_path, "image_" + str(accum_train_num))

        if not os.path.exists(save_path):
            os.mkdir(save_path)
        save_npy_files(save_path, train_set)

        accum_train_num += 1 

        # index = end_index

    # width = len(str(image_num - train_image_num))

    for index in valid_indexs:
        start_index = index
        end_index = index + 1

        # end_index = min(end_index, image_num)

        valid_set = {
                "AtomType": atom_type[image_index[start_index] : image_index[end_index]],
                "AtomTypeMap": atom_type_map[image_index[start_index] : image_index[end_index]],
                "ImageDR": image_dR[image_index[start_index] : image_index[end_index]],
                "ListNeighbor": list_neigh[image_index[start_index] : image_index[end_index]],
                # "NeighborType": neigh_type[image_index[start_index] : image_index[end_index]],
                "Ei": Ei[image_index[start_index] : image_index[end_index]],
                # "Ri": Ri[image_index[start_index] : image_index[end_index]],
                # "Ri_d": Ri_d[image_index[start_index] : image_index[end_index]],
                "Force": Force[image_index[start_index] : image_index[end_index]],
                "Etot": Etot[start_index:end_index],
                "ImageAtomNum": atom_num_per_image[start_index:end_index],
            }
        
        if Egroup is not None:
            valid_set["Egroup"] = Egroup[image_index[start_index] : image_index[end_index]]
            # valid_set["Divider"] = divider[image_index[start_index] : image_index[end_index]]
            valid_set["Divider"] = Divider[image_index[start_index] : image_index[end_index]]
            # valid_set["Egroup_weight"] = np.vstack(tuple(egroup_single_arr[image_index[start_index] : image_index[end_index]]))
            valid_set["Egroup_weight"] = Egroup_weight[image_index[start_index] : image_index[end_index]]
        if Virial is not None:
            valid_set["Virial"] = Virial[start_index:end_index]

        save_path = os.path.join(valid_data_path, "image_" + str(accum_valid_num))

        if not os.path.exists(save_path):
            os.mkdir(save_path)
        save_npy_files(save_path, valid_set)
        # index = end_index
        accum_valid_num += 1

    print("Saving npy file done")

    Rij_max = max_ri # for model compress
    return accum_train_num, accum_valid_num, Rij_max
********************************************* disuse **********************************"""
