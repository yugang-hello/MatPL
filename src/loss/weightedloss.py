from src.user.input_param import InputParam

def weighted_loss(dp_param: InputParam, stat, *args):
    # 根据不同的统计类型解析参数
    if stat == 1:
        has_fi, lossFi, has_etot, loss_Etot, has_virial, loss_Virial, has_egroup, loss_Egroup, has_ei, loss_Ei, natoms_sum = args
    elif stat == 2:  # 无 virial
        has_fi, lossFi, has_etot, loss_Etot, has_egroup, loss_Egroup, has_ei, loss_Ei, natoms_sum = args
    elif stat == 3:  # 无 egroup
        has_fi, lossFi, has_etot, loss_Etot, has_virial, loss_Virial, has_ei, loss_Ei, natoms_sum = args
    else:            # 无 virial 和 egroup
        has_fi, lossFi, has_etot, loss_Etot, has_ei, loss_Ei, natoms_sum = args

    # 直接从参数获取固定权重系数
    pref_fi = has_fi * dp_param.optimizer_param.start_pre_fac_force
    pref_etot = has_etot * dp_param.optimizer_param.start_pre_fac_etot
    pref_ei = has_ei * dp_param.optimizer_param.start_pre_fac_ei
    
    # 初始化损失值
    l2_loss = 0.0
    
    # 力损失项
    if has_fi:
        l2_loss += pref_fi * lossFi
    
    # 总能量损失项
    if has_etot:
        l2_loss += (1.0 / natoms_sum) * pref_etot * loss_Etot
    
    # 应力损失项（仅当 stat=1 或 3 时存在）
    if stat in (1, 3) and has_virial:
        pref_virial = has_virial * dp_param.optimizer_param.start_pre_fac_virial
        l2_loss += (1.0 / natoms_sum) * pref_virial * loss_Virial
    
    # 分组能量损失项（仅当 stat=1 或 2 时存在）
    if stat in (1, 2) and has_egroup:
        pref_egroup = has_egroup * dp_param.optimizer_param.start_pre_fac_egroup
        l2_loss += pref_egroup * loss_Egroup
    
    # 原子能量损失项
    if has_ei:
        l2_loss += pref_ei * loss_Ei

    return l2_loss, pref_fi, pref_etot
