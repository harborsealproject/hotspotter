from helpers import printWARN, printINFO
from warnings import catch_warnings, simplefilter 
import cv2
import numpy.linalg as linalg
import numpy as np
import scipy 
import scipy.linalg
import scipy.sparse as sparse
import scipy.sparse.linalg as sparse_linalg
# skimage.transform
# http://stackoverflow.com/questions/11462781/fast-2d-rigid-body-transformations-in-numpy-scipy
# skimage.transform.fast_homography(im, H)
def reload_module():
    import imp
    import sys
    imp.reload(sys.modules[__name__])
def rrr():
    reload_module()

# Generate 6 degrees of freedom homography transformation
def compute_homog(x1_mn, y1_mn, x2_mn, y2_mn):
    'Computes homography from normalized (0 to 1) point correspondences'
#with helpers.Timer('computehomog'):
    num_pts = len(x1_mn)
    Mbynine = np.zeros((2*num_pts,9), dtype=np.float32)
    for ix in xrange(num_pts): # Loop over inliers
        # Concatinate all 2x9 matrices into an Mx9 matrix
        u2      = x2_mn[ix]
        v2      = y2_mn[ix]
        (d,e,f) = (   -x1_mn[ix],    -y1_mn[ix],  -1)
        (g,h,i) = ( v2*x1_mn[ix],  v2*y1_mn[ix],  v2)
        (j,k,l) = (    x1_mn[ix],     y1_mn[ix],   1)
        (p,q,r) = (-u2*x1_mn[ix], -u2*y1_mn[ix], -u2)
        Mbynine[ix*2]   = (0, 0, 0, d, e, f, g, h, i)
        Mbynine[ix*2+1] = (j, k, l, 0, 0, 0, p, q, r)
    # Solve for the nullspace of the Mbynine
    try:
        (U, S, Vct) = linalg.svd(Mbynine)
    except MemoryError as ex:
        printWARN('Caught MemErr %r during full SVD. Trying sparse SVD.' % (ex))
        MbynineSparse = sparse.lil_matrix(Mbynine)
        (U, S, Vct) = sparse_linalg.svds(MbynineSparse)
    # Rearange the nullspace into a homography
    h = Vct[-1] # (transposed in matlab)
    H = np.vstack( ( h[0:3],  h[3:6],  h[6:9]  ) )
    return H
'''
if not 'xy_thresh' in vars():
    xy_thresh = .002
if not 'scale_thresh' in vars():
    scale_thresh = 2
if not 'min_num_inliers' in vars():
    min_num_inliers = 4
'''

'''
from hotspotter.spatial_verification2 import split_kpts
x_m, y_m = x2_m, y2_m
'''
def calc_diaglen_sqrd(x_m, y_m):
    x_extent_sqrd = (x_m.max() - x_m.min()) ** 2
    y_extent_sqrd = (y_m.max() - y_m.min()) ** 2
    diaglen_sqrd = x_extent_sqrd + y_extent_sqrd
    return diaglen_sqrd

def homography_inliers(kpts1, kpts2, fm, 
                       xy_thresh,
                       scale_thresh_high,
                       scale_thresh_low,
                       min_num_inliers=4, 
                       diaglen_sqrd=None):
    if len(fm) < min_num_inliers:
        return None
    # Not enough data
    # Estimate affine correspondence
    x1_m, y1_m, acd1_m = split_kpts(kpts1[fm[:, 0], :].T)
    x2_m, y2_m, acd2_m = split_kpts(kpts2[fm[:, 1], :].T)
    # TODO: Pass in the diag length
    if diaglen_sqrd is None:
        diaglen_sqrd = calc_diaglen_sqrd(x2_m, y2_m)
    xy_thresh_sqrd = diaglen_sqrd * xy_thresh
    print("sv2: xy_thresh_sqrd=%r" % xy_thresh_sqrd)
    print("sv2: scale_thresh_high=%r" % scale_thresh_high)
    print("sv2: scale_thresh_low=%r" % scale_thresh_low)
    Aff, aff_inliers = __affine_inliers(x1_m, y1_m, acd1_m, 
                                   x2_m, y2_m, acd2_m,
                                   xy_thresh_sqrd, 
                                   scale_thresh_high,
                                   scale_thresh_low)
    # Cannot find good affine correspondence
    if len(aff_inliers) < min_num_inliers:
        return None
    # keypoint xy coordinates shape=(dim, num)
    def normalize_xy_points(x_m, y_m):
        'Returns a transformation to normalize points to mean=0, stddev=1'
        mean_x = x_m.mean() # center of mass
        mean_y = y_m.mean()
        sx = 1 /x_m.std()   # average xy magnitude
        sy = 1 / y_m.std()
        tx = -mean_x * sx
        ty = -mean_y * sy
        T = np.array([(sx, 0, tx),
                      (0, sy, ty),
                      (0,  0,  1)])
        x_norm = (x_m - mean_x) * sx
        y_norm = (y_m - mean_y) * sy
        return x_norm, y_norm, T
    # Get corresponding points and shapes
    x1_ma, y1_ma, acd1_m = split_kpts(kpts1[fm[aff_inliers, 0]].T)
    x2_ma, y2_ma, acd2_m = split_kpts(kpts2[fm[aff_inliers, 1]].T)
    # Normalize affine inliers
    x1_mn, y1_mn, T1 = normalize_xy_points(x1_ma, y1_ma)
    x2_mn, y2_mn, T2 = normalize_xy_points(x2_ma, y2_ma)
    H_prime = compute_homog(x1_mn, y1_mn, x2_mn, y2_mn)
    try: 
        # Computes ax = b
        # x = linalg.solve(a, b)
        H = linalg.solve(T2, H_prime).dot(T1) # Unnormalize
    except linalg.LinAlgError as ex:
        printWARN('Warning 285 '+repr(ex), )
        return np.eye(3), aff_inliers

    ((H11, H12, H13),
     (H21, H22, H23),
     (H31, H32, H33)) = H
    # Transform kpts1 to kpts2
    x1_mt   = H11*(x1_m) + H12*(y1_m) + H13
    y1_mt   = H21*(x1_m) + H22*(y1_m) + H23
    z1_mt   = H31*(x1_m) + H32*(y1_m) + H33
    # --- Find (Squared) Error ---
    xy_err = (x1_mt/z1_mt - x2_m)**2 + (y1_mt/z1_mt - y2_m)**2 
    # Estimate final inliers
    inliers, = np.where(xy_err < xy_thresh_sqrd)
    return H, inliers, Aff, aff_inliers

def split_kpts(kpts5xN):
    'breakup keypoints into position and shape'
    _xs   = kpts5xN[0]
    _ys   = kpts5xN[1]
    _acds = kpts5xN[2:5] 
    return _xs, _ys, _acds

# --------------------------------
# Linear algebra functions on lower triangular matrices
def det_acd(acd):
    'Lower triangular determinant'
    return acd[0] * acd[2]
def inv_acd(acd, det):
    'Lower triangular inverse'
    return np.array((acd[2], -acd[1], acd[0])) / det
def dot_acd(acd1, acd2): 
    'Lower triangular dot product'
    a = (acd1[0] * acd2[0])
    c = (acd1[1] * acd2[0] + acd1[2] * acd2[1])
    d = (acd1[2] * acd2[2])
    return np.array([a, c, d])
# --------------------------------

def __affine_inliers(x1_m, y1_m, acd1_m,
                     x2_m, y2_m, acd2_m, xy_thresh_sqrd, 
                     scale_thresh_high, scale_thresh_low):
    'Estimates inliers deterministically using elliptical shapes'
#with helpers.Timer('enume all'):
    best_inliers = []
    num_best_inliers = 0
    best_mx  = None
    # Get keypoint scales (determinant)
    det1_m = det_acd(acd1_m)
    det2_m = det_acd(acd2_m)
    # Compute all transforms from kpts1 to kpts2 (enumerate all hypothesis)
    inv2_m = inv_acd(acd2_m, det2_m)
    # The transform from kp1 to kp2 is given as:
    # A = inv(A2).dot(A1)
    Aff_list = dot_acd(inv2_m, acd1_m)
    # Compute scale change of all transformations 
    detAff_list = det_acd(Aff_list)
    # Test all hypothesis 
    for mx in xrange(len(x1_m)):
        # --- Get the mth hypothesis ---
        A11 = Aff_list[0,mx]
        A21 = Aff_list[1,mx]
        A22 = Aff_list[2,mx]
        Adet = detAff_list[mx]
        x1_hypo = x1_m[mx]
        x2_hypo = x2_m[mx]
        y1_hypo = y1_m[mx]
        y2_hypo = y2_m[mx]
        # --- Transform from kpts1 to kpts2 ---
        x1_mt   = x2_hypo + A11*(x1_m - x1_hypo)
        y1_mt   = y2_hypo + A21*(x1_m - x1_hypo) + A22*(y1_m - y1_hypo)
        # --- Find (Squared) Error ---
        xy_err    = (x1_mt - x2_m)**2 + (y1_mt - y2_m)**2 
        scale_err = Adet * det1_m / det2_m
        # --- Determine Inliers ---
        xy_inliers = xy_err < xy_thresh_sqrd 
        scale_inliers = np.logical_and(scale_err > scale_thresh_low,
                                       scale_err < scale_thresh_high)
        hypo_inliers, = np.where(np.logical_and(xy_inliers, scale_inliers))
        num_hypo_inliers = len(hypo_inliers)
        # --- Update Best Inliers ---
        if num_hypo_inliers > num_best_inliers:
            best_mx = mx 
            best_inliers = hypo_inliers
            num_best_inliers = num_hypo_inliers
    Aa, Ac, Ad = Aff_list[:, best_mx]
    x1  = x1_m[best_mx]
    y1  = y1_m[best_mx]
    x2  = x2_m[best_mx]
    y2  = y2_m[best_mx]
    best_Aff = np.array([(Aa,  0,  x2-Aa*x1      ),
                         (Ac, Ad,  y2-Ac*x1-Ad*y1),
                         ( 0,  0,               1)])
    return best_Aff, best_inliers


def show_inliers(hs, qcx, cx, inliers, title='inliers', **kwargs):
    import load_data2 as ld2
    df2.show_matches2(rchip1, rchip2, kpts1, kpts2, fm[inliers], title=title, **kwargs_)


def test_realdata():
    import numpy.linalg as linalg
    import numpy as np
    import scipy.sparse as sparse
    import scipy.sparse.linalg as sparse_linalg
    import load_data2
    import params
    import draw_func2 as df2
    import helpers
    import spatial_verification2 as sv2
    sv2.rrr()
    params.rrr()
    load_data2.rrr()
    df2.rrr()
    df2.reset()
    xy_thresh = params.__XY_THRESH__
    scale_thresh = params.__SCALE_THRESH__
    # Pick out some data
    if not 'hs' in vars():
        (hs, qcx, cx, fm, fs, rchip1, rchip2, kpts1, kpts2) = load_data2.get_sv_test_data()
    # Draw assigned matches
    df2.show_matches2(rchip1, rchip2, kpts1, kpts2, fm, fs=None,
                      all_kpts=False, draw_lines=False, doclf=True,
                      title='Assigned matches')
    df2.update()
    # Affine matching tests
    scale_thresh_low  = scale_thresh ** 2
    scale_thresh_high = 1.0 / scale_thresh_low
    # Split into location and shape
    x1_m, y1_m, acd1_m = split_kpts(kpts1[fm[:, 0]].T)
    x2_m, y2_m, acd2_m = split_kpts(kpts2[fm[:, 1]].T)
    # TODO: Pass in the diag length
    x2_extent = x2_m.max() - x2_m.min()
    y2_extent = y2_m.max() - y2_m.min()
    img2_extent = np.array([x2_extent, y2_extent])
    img2_diaglen_sqrd = x2_extent**2 + y2_extent**2
    xy_thresh_sqrd = img2_diaglen_sqrd * xy_thresh
    # -----------------------------------------------
    # Get match threshold 10% of matching keypoint extent diagonal
    aff_inliers1, Aff1 = sv2.affine_inliers(kpts1, kpts2, fm, xy_thresh, scale_thresh)
    # Draw affine inliers
    df2.show_matches2(rchip1, rchip2, kpts1, kpts2, fm[aff_inliers1], fs=None,
                      all_kpts=False, draw_lines=False, doclf=True,
                      title='Assigned matches')
    df2.update()
