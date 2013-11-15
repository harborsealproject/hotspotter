from __future__ import division, print_function
import match_chips3 as mc3
import matching_functions as mf
import DataStructures as ds
import investigate_chip as iv
import voting_rules2 as vr2
import draw_func2 as df2
import fileio as io
import chip_compute2 as cc2
import feature_compute2 as fc2
import load_data2 as ld2
import HotSpotter
import algos
import re
import Parallelize as parallel
from match_chips3 import *
import helpers as helpers
import numpy as np
import sys

# What are good ways we can divide up FLANN indexes instead of having one
# monolithic index? Divide up in terms of properties of the database chips

# Can also reduce the chips being indexed


# What happens when we take all other possible ground truth matches out
# of the database index? 


mc3.rrr(); mf.rrr(); iv.rrr(); ds.rrr(); vr2.rrr()
vr2.print_off()
mf.print_off()
algos.print_off()
io.print_off()
HotSpotter.print_off()
cc2.print_off()
fc2.print_off()
ld2.print_off()
helpers.print_off()
parallel.print_off()
mc3.print_off()

def get_test_results(hs, q_params, use_cache=True):
    query_uid = q_params.get_uid(True, True, True, True, True)
    hs_uid = hs.db_name()
    test_uid = hs_uid + query_uid
    io_kwargs = dict(dpath='results', fname='test_results', uid=test_uid, ext='.cPkl')
    if use_cache:
        test_results = io.smart_load(**io_kwargs)
        if not test_results is None: return test_results
    id2_qon = zip(*iv.get_all_history(hs.args.db, hs))
    id2_bestranks = []
    id2_algos = []
    id2_title = []
    nChips = hs.num_cx
    nNames = len(hs.tables.nx2_name) - 2
    for id_ in xrange(len(id2_qon)):
        print('------------')
        (qcx, ocids, notes) = id2_qon[id_]
        gt_cxs = hs.get_other_cxs(qcx)
        title = 'q'+ hs.cxstr(qcx) + ' - ' + notes
        print(title)
        print('gt_'+hs.cxstr(gt_cxs))
        res_list = mc3.execute_query_safe(hs, q_params, [qcx])
        bestranks = []
        algos = []
        for qcx2_res in res_list:
            res = qcx2_res[qcx]
            algos += [res.title]
            gt_ranks = res.get_gt_ranks(gt_cxs)
            print('cx_ranks(/%4r) = %r' % (nChips, gt_ranks))
            #print('ns_ranks(/%4r) = %r' % (nNames, gt_ranks))
            bestranks += [min(gt_ranks)]
        # record metadata
        id2_algos += [algos]
        id2_title += [title]
        id2_bestranks += [bestranks]
    id2_title     = np.array(id2_title)
    id2_bestranks = np.array(id2_bestranks)
    id2_title.shape = (len(id2_title), 1)
    col_lbls = id2_algos[0]
    row_lbls = id2_title
    mat_vals = id2_bestranks
    test_results = (col_lbls, row_lbls, mat_vals, test_uid)
    helpers.ensuredir('results')
    io.smart_save(test_results, **io_kwargs)
    return test_results

row2_best_params = None
row2_lbl = None
row2_best_col = None
row2_score = None
row2_colpos = None

def print_test_results(test_results):
    global row2_best_params
    global row2_best_col
    global row2_score
    global row2_lbl
    global row2_colpos
    (col_lbls, row_lbls, mat_vals, test_uid) = test_results
    test_uid = re.sub(r'_trainID\([0-9]*,........\)','', test_uid)
    test_uid = re.sub(r'_indxID\([0-9]*,........\)','', test_uid)
    test_uid = re.sub(r'HSDB_zebra_with_mothers','', test_uid)
    test_uid = re.sub(r'GZ_ALL','', test_uid)
    test_uid = re.sub(r'HESAFF_sz750','', test_uid)
    if row2_best_params is None: 
        row2_best_params = ['' for _ in xrange(len(row_lbls))]
        row2_lbl         = ['' for _ in xrange(len(row_lbls))]
        row2_colpos      = ['' for _ in xrange(len(row_lbls))]
        row2_best_col    = -np.ones(len(row_lbls))
        row2_score       = -np.ones(len(row_lbls))
    best_vals = mat_vals.min(1)
    best_mat = np.tile(best_vals, (len(mat_vals.T), 1)).T
    best_pos = (best_mat == mat_vals)
    for row, val in enumerate(best_vals):
        if val == row2_score[row]:
            colpos = np.where(best_pos[row])[0].min()
            row2_best_params[row] += '*'
            row2_best_params[row] += '\n**'+test_uid+'c'+str(colpos)+'*'
        if val < row2_score[row]  or row2_score[row] == -1:
            row2_score[row] = val
            colpos = np.where(best_pos[row])[0].min()
            row2_best_params[row] = test_uid+'c'+str(colpos)+'*'
            row2_lbl[row] = row_lbls[row]
            row2_colpos[row] = colpos
    print('----------------------')
    print('test_uid=%r' % test_uid)
    #print('row_lbls=\n%s' % str(row_lbls))
    #print('col_lbls=\n%s' % str('\n  '.join(col_lbls)))
    print('mat_vals=\n%s' % str(mat_vals))

def print_best():
    global row2_score
    global row2_best_params
    global row2_lbl
    for row in xrange(len(row2_lbl)):
        print('-------------')
        print('rowlbl(%d): %s' % (row, row2_lbl[row]))
        print('best_params = %s' % (row2_best_params[row],))
        print('best_score(c%r) = %r' % (row2_colpos[row], row2_score[row],))

def all_dict_combinations(varied_dict):
    from itertools import product as iprod
    viter = varied_dict.iteritems()
    tups_list = [[(key,val) for val in val_list] for (key, val_list) in viter]
    dict_list = [{key:val for (key,val) in tups} for tups in iprod(*tups_list)]
    return dict_list

def test_scoring(hs):
    varied_params = {
        'lnbnn_weight' : [0],
        'checks'       : [128, 1024],
        'Krecip'       : [0, 5],
        'K'            : [5, 10],
    }
    dict_list = all_dict_combinations(varied_params)
    test_list = [ds.QueryParams(**_dict) for _dict in dict_list]
    io.print_off()
    for test in test_list:
        results = get_test_results(hs, test, use_cache=True)
        print_test_results(results)
    print_best()
    #print(np.hstack([id2_bestranks, id2_title]))
    #execute_query_safe(

if __name__ == '__main__':
    import multiprocessing
    multiprocessing.freeze_support()
    main_locals = iv.main()
    execstr = helpers.execstr_dict(main_locals, 'main_locals')
    exec(execstr)
    test_scoring(hs)
    #for vals in vr2.TMP:
        #print('-----')
        #for val in vals:
            #print(val)
        #print('-----')
    exec(df2.present())
