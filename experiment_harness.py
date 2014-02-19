from __future__ import division, print_function
# Python
import sys
import itertools
import textwrap
from os.path import join
from itertools import imap
# Scientific
import numpy as np
# Hotspotter
import experiment_configs
from hotspotter import Config
from hotspotter import DataStructures as ds
from hotspotter import match_chips3 as mc3
from hscom import fileio as io
from hscom import helpers as util
from hscom import latex_formater
from hscom import params
from hsviz import draw_func2 as df2
#from match_chips3 import *
#import draw_func2 as df2
# What are good ways we can divide up FLANN indexes instead of having one
# monolithic index? Divide up in terms of properties of the database chips

# Can also reduce the chips being indexed

# What happens when we take all other possible ground truth matches out
# of the database index?


def get_valid_testcfg_names():
    testcfg_keys = vars(experiment_configs).keys()
    testcfg_locals = [key for key in testcfg_keys if key.find('_') != 0]
    valid_cfg_names = util.indent('\n'.join(testcfg_locals), '  * ')
    return valid_cfg_names


def get_vary_dicts(test_cfg_name_list):
    vary_dicts = []
    for cfg_name in test_cfg_name_list:
        test_cfg = experiment_configs.__dict__[cfg_name]
        vary_dicts.append(test_cfg)
    if len(vary_dicts) == 0:
        valid_cfg_names = get_valid_testcfg_names()
        raise Exception('Choose a valid testcfg:\n' + valid_cfg_names)
    return vary_dicts


__QUIET__ = '--quiet' in sys.argv

#---------
# Helpers
#---------------
# Display Test Results


def ArgGaurdFalse(func):
    return __ArgGaurd(func, default=False)


def ArgGaurdTrue(func):
    return __ArgGaurd(func, default=True)


def __ArgGaurd(func, default=False):
    flag = func.func_name
    if flag.find('no') == 0:
        flag = flag[2:]
    flag = '--' + flag.replace('_', '-')

    def GaurdWrapper(*args, **kwargs):
        if util.get_flag(flag, default):
            return func(*args, **kwargs)
        else:
            if not __QUIET__:
                print('\n~~~ %s ~~~\n' % flag)
    GaurdWrapper.func_name = func.func_name
    return GaurdWrapper


def rankscore_str(thresh, nLess, total):
    #helper to print rank scores of configs
    percent = 100 * nLess / total
    fmtsf = '%' + str(util.num2_sigfig(total)) + 'd'
    fmtstr = '#ranks < %d = ' + fmtsf + '/%d = (%.1f%%) (err=' + fmtsf + ')'
    rankscore_str = fmtstr % (thresh, nLess, total, percent, (total - nLess))
    return rankscore_str


def wrap_uid(uid):
    import re
    # REGEX to locate _XXXX(
    cfg_regex = r'_[A-Z][A-Z]*\('
    uidmarker_list = re.findall(cfg_regex, uid)
    uidconfig_list = re.split(cfg_regex, uid)
    args = [uidconfig_list, uidmarker_list]
    interleave_iter = util.interleave(args)
    new_uid_list = []
    total_len = 0
    prefix_str = ''
    # If unbalanced there is a prefix before a marker
    if len(uidmarker_list) < len(uidconfig_list):
        frag = interleave_iter.next()
        new_uid_list += [frag]
        total_len = len(frag)
        prefix_str = ' ' * len(frag)
    # Iterate through markers and config strings
    while True:
        try:
            marker_str = interleave_iter.next()
            config_str = interleave_iter.next()
            frag = marker_str + config_str
        except StopIteration:
            break
        total_len += len(frag)
        new_uid_list += [frag]
        # Go to newline if past 80 chars
        if total_len > 80:
            total_len = 0
            new_uid_list += ['\n' + prefix_str]
    wrapped_uid = ''.join(new_uid_list)
    return wrapped_uid


def format_uid_list(uid_list):
    indented_list = util.indent_list('    ', uid_list)
    wrapped_list = imap(wrap_uid, indented_list)
    return util.joins('\n', wrapped_list)


#---------------
# Display Test Results
#-----------
# Run configuration for each query
def get_test_results(hs, qcx_list, qdat, cfgx=0, nCfg=1, nocache_testres=False,
                     test_results_verbosity=2):
    nQuery = len(qcx_list)
    dcxs = hs.get_indexed_sample()
    query_uid = qdat.get_uid()
    hs_uid    = hs.get_db_name()
    qcxs_uid  = util.hashstr_arr(qcx_list, lbl='_qcxs')
    test_uid  = hs_uid + query_uid + qcxs_uid
    cache_dir = join(hs.dirs.cache_dir, 'experiment_harness_results')
    io_kwargs = dict(dpath=cache_dir, fname='test_results', uid=test_uid,
                     ext='.cPkl')

    if test_results_verbosity == 2:
        print('[harn] get_test_results(): %r' % query_uid)
    #io.print_on()

    # High level caching
    if not params.args.nocache_query and (not nocache_testres):
        qx2_bestranks = io.smart_load(**io_kwargs)
        if qx2_bestranks is None:
            print('[harn] Cache returned None!')
        elif len(qx2_bestranks) != len(qcx_list):
            print('[harn] Re-Caching qx2_bestranks')
        elif not qx2_bestranks is None:
            return qx2_bestranks, [[{0: None}]] * nQuery
        #raise Exception('cannot be here')

    nPrevQ = nQuery * cfgx
    qx2_bestranks = []
    qx2_reslist = []

    # Make progress message
    msg = textwrap.dedent('''
    ---------------------
    [harn] TEST %d/%d
    ---------------------''')
    mark_progress = util.simple_progres_func(test_results_verbosity, msg, '.')
    total = nQuery * nCfg
    # Perform queries
    TEST_INFO = True
    # Query Chip / Row Loop
    for qx, qcx in enumerate(qcx_list):
        count = qx + nPrevQ + 1
        mark_progress(count, total)
        if TEST_INFO:
            print('qcx=%r. quid=%r' % (qcx, qdat.get_uid()))
        res_list = mc3.execute_query_safe(hs, qdat, [qcx], dcxs)
        qx2_reslist += [res_list]
        assert len(res_list) == 1
        bestranks = []
        for qcx2_res in res_list:
            assert len(qcx2_res) == 1
            res = qcx2_res[qcx]
            gt_ranks = res.get_gt_ranks(hs=hs)
            #print('[harn] cx_ranks(/%4r) = %r' % (nChips, gt_ranks))
            #print('[harn] cx_ranks(/%4r) = %r' % (NMultiNames, gt_ranks))
            #print('ns_ranks(/%4r) = %r' % (nNames, gt_ranks))
            _bestrank = -1 if len(gt_ranks) == 0 else min(gt_ranks)
            bestranks += [_bestrank]
        # record metadata
        qx2_bestranks += [bestranks]
        if qcx % 4 == 0:
            sys.stdout.flush()
    print('')
    qx2_bestranks = np.array(qx2_bestranks)
    # High level caching
    util.ensuredir(cache_dir)
    io.smart_save(qx2_bestranks, **io_kwargs)

    return qx2_bestranks, qx2_reslist


def get_varied_params_list(test_cfg_name_list):
    vary_dicts = get_vary_dicts(test_cfg_name_list)
    get_all_dict_comb = util.all_dict_combinations
    dict_comb_list = [get_all_dict_comb(_dict) for _dict in vary_dicts]
    varied_params_list = [comb for dict_comb in dict_comb_list for comb in dict_comb]
    #map(lambda x: print('\n' + str(x)), varied_params_list)
    return varied_params_list


def get_cfg_list(hs, test_cfg_name_list):
    print('[harn] building cfg_list: %s' % test_cfg_name_list)
    if 'custom' == test_cfg_name_list:
        print('   * custom cfg_list')
        cfg_list = [hs.prefs.query_cfg]
        return cfg_list
    varied_params_list = get_varied_params_list(test_cfg_name_list)
    # Add unique configs to the list
    cfg_list = []
    cfg_set = set([])
    for _dict in varied_params_list:
        cfg = Config.QueryConfig(**_dict)
        if not cfg in cfg_set:
            cfg_list.append(cfg)
            cfg_set.add(cfg)
    if not __QUIET__:
        print('[harn] reduced equivilent cfgs %d / %d cfgs' % (len(cfg_list),
                                                               len(varied_params_list)))

    return cfg_list


#-----------
def test_configurations(hs, qcx_list, test_cfg_name_list, fnum=1):

    # Test Each configuration
    if not __QUIET__:
        print(textwrap.dedent("""
        [harn]================
        [harn] experiment_harness.test_configurations()""").strip())

    hs.update_samples()

    # Grab list of algorithm configurations to test
    cfg_list = get_cfg_list(hs, test_cfg_name_list)
    if not __QUIET__:
        print('[harn] Testing %d different parameters' % len(cfg_list))
        print('[harn]         %d different chips' % len(qcx_list))

    # Preallocate test result aggregation structures
    sel_cols = params.args.sel_cols  # FIXME
    sel_rows = params.args.sel_rows  # FIXME
    sel_cols = [] if sel_cols is None else sel_cols
    sel_rows = [] if sel_rows is None else sel_rows
    nCfg     = len(cfg_list)
    nQuery   = len(qcx_list)
    #rc2_res  = np.empty((nQuery, nCfg), dtype=list)  # row/col -> result
    mat_list = []
    qdat     = ds.QueryData()

    nocache_testres =  util.get_flag('--nocache-testres', False)

    test_results_verbosity = 2 - __QUIET__
    test_cfg_verbosity = 2

    msg = textwrap.dedent('''
    ---------------------')
    [harn] TEST_CFG %d/%d'
    ---------------------''')
    mark_progress = util.simple_progres_func(test_cfg_verbosity, msg, '+')

    uid2_query_cfg = {}

    nomemory = params.args.nomemory

    # Run each test configuration
    # Query Config / Col Loop
    for cfgx, query_cfg in enumerate(cfg_list):
        mark_progress(cfgx + 1, nCfg)
        # Set data to the current config
        #print(query_cfg.get_printable())
        qdat.set_cfg(query_cfg, hs=hs)
        #_nocache_testres = nocache_testres or (cfgx in sel_cols)
        dcxs = hs.get_indexed_sample()
        mc3.prepare_qdat_indexes(qdat, None, dcxs)
        uid2_query_cfg[qdat.get_uid()] = query_cfg
        # Run the test / read cache
        qx2_bestranks, qx2_reslist = get_test_results(hs, qcx_list, qdat, cfgx,
                                                      nCfg, nocache_testres,
                                                      test_results_verbosity)
        if nomemory:
            continue
        # Store the results
        mat_list.append(qx2_bestranks)
        #for qx, reslist in enumerate(qx2_reslist):
            #assert len(reslist) == 1
            #qcx2_res = reslist[0]
            #assert len(qcx2_res) == 1
            #res = qcx2_res.values()[0]
            #rc2_res[qx, cfgx] = res

    if not __QUIET__:
        print('[harn] Finished testing parameters')
    if nomemory:
        print('ran tests in memory savings mode. exiting')
        return
    #--------------------
    # Print Best Results
    rank_mat = np.hstack(mat_list)
    # Label the rank matrix:
    _colxs = np.arange(nCfg)
    lbld_mat = np.vstack([_colxs, rank_mat])
    _rowxs = np.arange(nQuery + 1).reshape(nQuery + 1, 1) - 1
    lbld_mat = np.hstack([_rowxs, lbld_mat])
    #------------
    # Build row labels
    qx2_lbl = []
    for qx in xrange(nQuery):
        qcx = qcx_list[qx]
        label = 'qx=%d) q%s ' % (qx, hs.cidstr(qcx, notes=True))
        qx2_lbl.append(label)
    qx2_lbl = np.array(qx2_lbl)
    #------------
    # Build col labels
    cfgx2_lbl = []
    for cfgx in xrange(nCfg):
        test_uid  = cfg_list[cfgx].get_uid()
        test_uid  = cfg_list[cfgx].get_uid()
        cfg_label = 'cfgx=(%3d) %s' % (cfgx, test_uid)
        cfgx2_lbl.append(cfg_label)
    cfgx2_lbl = np.array(cfgx2_lbl)
    #------------
    indent = util.indent

    @ArgGaurdFalse
    def print_rowlbl():
        print('=====================')
        print('[harn] Row/Query Labels')
        print('=====================')
        print('[harn] queries:\n%s' % '\n'.join(qx2_lbl))
        print('--- /Row/Query Labels ---')
    print_rowlbl()

    #------------

    @ArgGaurdFalse
    def print_collbl():
        print('')
        print('=====================')
        print('[harn] Col/Config Labels')
        print('=====================')
        print('[harn] configs:\n%s' % '\n'.join(cfgx2_lbl))
        print('--- /Col/Config Labels ---')
    print_collbl()

    #------------
    # Build Colscore
    qx2_min_rank = []
    qx2_argmin_rank = []
    new_hard_qx_list = []
    new_qcid_list = []
    new_hardtup_list = []
    for qx in xrange(nQuery):
        ranks = rank_mat[qx]
        min_rank = ranks.min()
        bestCFG_X = np.where(ranks == min_rank)[0]
        qx2_min_rank.append(min_rank)
        qx2_argmin_rank.append(bestCFG_X)
        # Mark examples as hard
        if ranks.max() > 0:
            new_hard_qx_list += [qx]
    for qx in new_hard_qx_list:
        # New list is in cid format instead of cx format
        # because you should be copying and pasting it
        notes = ' ranks = ' + str(rank_mat[qx])
        qcx = qcx_list[qx]
        qcid = hs.tables.cx2_cid[qcx]
        new_hardtup_list += [(qcid, notes)]
        new_qcid_list += [qcid]

    @ArgGaurdFalse
    def print_rowscore():
        print('')
        print('=======================')
        print('[harn] Scores per Query')
        print('=======================')
        for qx in xrange(nQuery):
            bestCFG_X = qx2_argmin_rank[qx]
            min_rank = qx2_min_rank[qx]
            minimizing_cfg_str = indent('\n'.join(cfgx2_lbl[bestCFG_X]), '    ')
            #minimizing_cfg_str = str(bestCFG_X)

            print('-------')
            print(qx2_lbl[qx])
            print(' best_rank = %d ' % min_rank)
            if len(cfgx2_lbl) != 1:
                print(' minimizing_cfg_x\'s = %s ' % minimizing_cfg_str)

    print_rowscore()

    #------------

    @ArgGaurdFalse
    def print_hardcase():
        print('===')
        print('--- hard new_hardtup_list (w.r.t these configs) ---')
        print('\n'.join(map(repr, new_hardtup_list)))
        print('There are %d hard cases ' % len(new_hardtup_list))
        print(sorted([x[0] for x in new_hardtup_list]))
        print('--- /Print Hardcase ---')
    print_hardcase()

    @ArgGaurdFalse
    def echo_hardcase():
        print('====')
        print('--- hardcase commandline ---')
        hardcids_str = ' '.join(map(str, ['    ', '--qcid'] + new_qcid_list))
        print(hardcids_str)
        print('--- /Echo Hardcase ---')
    echo_hardcase()

    #------------
    # Build Colscore
    X_list = [1, 5]
    # Build a dictionary mapping X (as in #ranks < X) to a list of cfg scores
    nLessX_dict = {int(X): np.zeros(nCfg) for X in iter(X_list)}
    for cfgx in xrange(nCfg):
        ranks = rank_mat[:, cfgx]
        for X in iter(X_list):
            #nLessX_ = sum(np.bitwise_and(ranks < X, ranks >= 0))
            nLessX_ = sum(np.logical_and(ranks < X, ranks >= 0))
            nLessX_dict[int(X)][cfgx] = nLessX_

    @ArgGaurdFalse
    def print_colscore():
        print('')
        print('==================')
        print('[harn] Scores per Config')
        print('==================')
        for cfgx in xrange(nCfg):
            print('[score] %s' % (cfgx2_lbl[cfgx]))
            for X in iter(X_list):
                nLessX_ = nLessX_dict[int(X)][cfgx]
                print('        ' + rankscore_str(X, nLessX_, nQuery))
        print('--- /Scores per Config ---')
    print_colscore()

    #------------

    @ArgGaurdFalse
    def print_latexsum():
        print('')
        print('==========================')
        print('[harn] LaTeX')
        print('==========================')
        # Create configuration latex table
        criteria_lbls = ['#ranks < %d' % X for X in X_list]
        db_name = hs.get_db_name(True)
        cfg_score_title = db_name + ' rank scores'
        cfgscores = np.array([nLessX_dict[int(X)] for X in X_list]).T

        replace_rowlbl = [(' *cfgx *', ' ')]
        tabular_kwargs = dict(title=cfg_score_title, out_of=nQuery,
                              bold_best=True, replace_rowlbl=replace_rowlbl,
                              flip=True)
        tabular_str = latex_formater.make_score_tabular(cfgx2_lbl,
                                                        criteria_lbls,
                                                        cfgscores,
                                                        **tabular_kwargs)
        #latex_formater.render(tabular_str)
        print(tabular_str)
        print('--- /LaTeX ---')
    print_latexsum()

    #------------
    best_rankscore_summary = []
    to_intersect_list = []
    # print each configs scores less than X=thresh
    for X, cfgx2_nLessX in nLessX_dict.iteritems():
        max_LessX = cfgx2_nLessX.max()
        bestCFG_X = np.where(cfgx2_nLessX == max_LessX)[0]
        best_rankscore = '[cfg*] %d cfg(s) scored ' % len(bestCFG_X)
        best_rankscore += rankscore_str(X, max_LessX, nQuery)
        best_rankscore_summary += [best_rankscore]
        to_intersect_list += [cfgx2_lbl[bestCFG_X]]

    intersected = to_intersect_list[0] if len(to_intersect_list) > 0 else []
    for ix in xrange(1, len(to_intersect_list)):
        intersected = np.intersect1d(intersected, to_intersect_list[ix])

    @ArgGaurdFalse
    def print_bestcfg():
        print('')
        print('==========================')
        print('[harn] Best Configurations')
        print('==========================')
        # print each configs scores less than X=thresh
        for X, cfgx2_nLessX in nLessX_dict.iteritems():
            max_LessX = cfgx2_nLessX.max()
            bestCFG_X = np.where(cfgx2_nLessX == max_LessX)[0]
            best_rankscore = '[cfg*] %d cfg(s) scored ' % len(bestCFG_X)
            best_rankscore += rankscore_str(X, max_LessX, nQuery)
            uid_list = cfgx2_lbl[bestCFG_X]

            #best_rankcfg = ''.join(map(wrap_uid, uid_list))
            best_rankcfg = format_uid_list(uid_list)
            #indent('\n'.join(uid_list), '    ')
            print(best_rankscore)
            print(best_rankcfg)

        print('[cfg*]  %d cfg(s) are the best of %d total cfgs' % (len(intersected), nCfg))
        print(format_uid_list(intersected))

        print('--- /Best Configurations ---')
    print_bestcfg()

    #------------

    @ArgGaurdFalse
    def print_rankmat():
        print('')
        print('[harn]-------------')
        print('[harn] nRows=%r, nCols=%r' % lbld_mat.shape)
        print('[harn] labled rank matrix: rows=queries, cols=cfgs:')
        #np.set_printoptions(threshold=5000, linewidth=5000, precision=5)
        with util.NpPrintOpts(threshold=5000, linewidth=5000, precision=5):
            print(lbld_mat)
        print('[harn]-------------')
    print_rankmat()

    #------------
    print('')
    print('+===========================')
    print('| [cfg*] SUMMARY       ')
    print('|---------------------------')
    print(util.joins('\n| ', best_rankscore_summary))
    print('+===========================')
    #print('--- /SUMMARY ---')

    # Draw results
    if not __QUIET__:
        print('remember to inspect with --sel-rows (-r) and --sel-cols (-c) ')
    if len(sel_rows) > 0 and len(sel_cols) == 0:
        sel_cols = range(len(cfg_list))
    if len(sel_cols) > 0 and len(sel_rows) == 0:
        sel_rows = range(len(qcx_list))
    if params.args.view_all:
        sel_rows = range(len(qcx_list))
        sel_cols = range(len(cfg_list))
    sel_cols = list(sel_cols)
    sel_rows = list(sel_rows)
    total = len(sel_cols) * len(sel_rows)
    rciter = itertools.product(sel_rows, sel_cols)

    prev_cfg = None

    skip_to = util.get_arg('--skip-to', default=None)

    dev_mode = util.get_arg('--devmode', default=False)
    skip_list = []
    if dev_mode:
        hs.prefs.display_cfg.N = 3
        df2.FONTS.axtitle = df2.FONTS.smaller
        df2.FONTS.xlabel = df2.FONTS.smaller
        df2.FONTS.figtitle = df2.FONTS.smaller
        df2.SAFE_POS['top']    = .8
        df2.SAFE_POS['bottom'] = .01

    for count, (r, c) in enumerate(rciter):
        if skip_to is not None:
            if count < skip_to:
                continue
        if count in skip_list:
            continue
        # Get row and column index
        qcx       = qcx_list[r]
        query_cfg = cfg_list[c]
        print('\n\n___________________________________')
        print('      --- VIEW %d / %d ---        '
              % (count + 1, total))
        print('--------------------------------------')
        print('viewing (r, c) = (%r, %r)' % (r, c))
        # Load / Execute the query
        qdat = mc3.prepare_qdat_cfg(hs, qdat, query_cfg)
        mc3.prepare_qdat_indexes(qdat, None, dcxs)
        res_list = mc3.execute_query_safe(hs, qdat, [qcx], dcxs)
        res = res_list[0][qcx]
        # Print Query UID
        print(res.true_uid)
        # Draw Result
        #res.show_top(hs, fnum=fnum)
        if prev_cfg != query_cfg:
            # This is way too aggro. Needs to be a bit lazier
            hs.refresh_features()
        prev_cfg = query_cfg
        fnum = count
        title_uid = res.true_uid
        title_uid = title_uid.replace('_FEAT', '\n_FEAT')
        res.show_analysis(hs, fnum=fnum, aug='\n' + title_uid, annote=1,
                          show_name=False, show_gname=False, time_appart=False)
        df2.adjust_subplots_safe()
        if params.args.save_figures:
            from hsviz import allres_viz
            allres_viz.dump(hs, 'analysis', quality=True, overwrite=False)
    if not __QUIET__:
        print('[harn] EXIT EXPERIMENT HARNESS')
