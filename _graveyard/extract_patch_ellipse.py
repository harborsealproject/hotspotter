
def in_depth_ellipse2x2(rchip, kp):
    #-----------------------
    # SETUP
    #-----------------------
    from hotspotter import draw_func2 as df2
    np.set_printoptions(precision=8)
    tau = 2 * np.pi
    df2.reset()
    df2.figure(9003, docla=True, doclf=True)
    ax = df2.gca()
    ax.invert_yaxis()

    def _plotpts(data, px, color=df2.BLUE, label=''):
        #df2.figure(9003, docla=True, pnum=(1, 1, px))
        df2.plot2(data.T[0], data.T[1], '.', '', color=color, label=label)
        df2.update()

    def _plotarrow(x, y, dx, dy, color=df2.BLUE, label=''):
        ax = df2.gca()
        arrowargs = dict(head_width=.5, length_includes_head=True, label=label)
        arrow = df2.FancyArrow(x, y, dx, dy, **arrowargs)
        arrow.set_edgecolor(color)
        arrow.set_facecolor(color)
        ax.add_patch(arrow)
        df2.update()

    def _2x2_eig(M2x2):
        (evals, evecs) = np.linalg.eig(M2x2)
        l1, l2 = evals
        v1, v2 = evecs
        return l1, l2, v1, v2

    #-----------------------
    # INPUT
    #-----------------------
    # We will call perdoch's invA = invV
    print('--------------------------------')
    print('Let V = Perdoch.A')
    print('Let Z = Perdoch.E')
    print('--------------------------------')
    print('Input from Perdoch\'s detector: ')

    # We are given the keypoint in invA format
    (x, y, ia11, ia21, ia22), ia12 = kp, 0
    invV = np.array([[ia11, ia12],
                     [ia21, ia22]])
    V = np.linalg.inv(invV)
    # <HACK>
    #invV = V / np.linalg.det(V)
    #V = np.linalg.inv(V)
    # </HACK>
    Z = (V.T).dot(V)

    print('invV is a transform from points on a unit-circle to the ellipse')
    util.horiz_print('invV = ', invV)
    print('--------------------------------')
    print('V is a transformation from points on the ellipse to a unit circle')
    util.horiz_print('V = ', V)
    print('--------------------------------')
    print('Points on a matrix satisfy (x).T.dot(Z).dot(x) = 1')
    print('where Z = (V.T).dot(V)')
    util.horiz_print('Z = ', Z)

    # Define points on a unit circle
    theta_list = np.linspace(0, tau, 50)
    cicrle_pts = np.array([(np.cos(t), np.sin(t)) for t in theta_list])

    # Transform those points to the ellipse using invV
    ellipse_pts1 = invV.dot(cicrle_pts.T).T

    # Transform those points to the ellipse using V
    ellipse_pts2 = V.dot(cicrle_pts.T).T

    #Lets check our assertion: (x_).T.dot(Z).dot(x_) = 1
    checks1 = [x_.T.dot(Z).dot(x_) for x_ in ellipse_pts1]
    checks2 = [x_.T.dot(Z).dot(x_) for x_ in ellipse_pts2]
    assert all([abs(1 - check) < 1E-11 for check in checks1])
    #assert all([abs(1 - check) < 1E-11 for check in checks2])
    print('... all of our plotted points satisfy this')

    #=======================
    # THE CONIC SECTION
    #=======================
    # All of this was from the Perdoch paper, now lets move into conic sections
    # We will use the notation from wikipedia
    # http://en.wikipedia.org/wiki/Conic_section
    # http://en.wikipedia.org/wiki/Matrix_representation_of_conic_sections

    #-----------------------
    # MATRIX REPRESENTATION
    #-----------------------
    # The matrix representation of a conic is:
    (A,  B2, B2_, C) = Z.flatten()
    (D, E, F) = (0, 0, 1)
    B = B2 * 2
    assert B2 == B2_, 'matrix should by symmetric'
    print('--------------------------------')
    print('Now, using wikipedia\' matrix representation of a conic.')
    con = np.array((('    A', 'B / 2', 'D / 2'),
                    ('B / 2', '    C', 'E / 2'),
                    ('D / 2', 'E / 2', '    F')))
    util.horiz_print('A matrix A_Q = ', con)

    # A_Q is our conic section (aka ellipse matrix)
    A_Q = np.array(((    A, B / 2, D / 2),
                    (B / 2,     C, E / 2),
                    (D / 2, E / 2,     F)))

    util.horiz_print('A_Q = ', A_Q)

    #-----------------------
    # DEGENERATE CONICS
    #-----------------------
    print('----------------------------------')
    print('As long as det(A_Q) != it is not degenerate.')
    print('If the conic is not degenerate, we can use the 2x2 minor: A_33')
    print('det(A_Q) = %s' % str(np.linalg.det(A_Q)))
    assert np.linalg.det(A_Q) != 0, 'degenerate conic'
    A_33 = np.array(((    A, B / 2),
                     (B / 2,     C)))
    util.horiz_print('A_33 = ', A_33)

    #-----------------------
    # CONIC CLASSIFICATION
    #-----------------------
    print('----------------------------------')
    print('The determinant of the minor classifies the type of conic it is')
    print('(det == 0): parabola, (det < 0): hyperbola, (det > 0): ellipse')
    print('det(A_33) = %s' % str(np.linalg.det(A_33)))
    assert np.linalg.det(A_33) > 0, 'conic is not an ellipse'
    print('... this is indeed an ellipse')

    #-----------------------
    # CONIC CENTER
    #-----------------------
    print('----------------------------------')
    print('the centers of the ellipse are obtained by: ')
    print('x_center = (B * E - (2 * C * D)) / (4 * A * C - B ** 2)')
    print('y_center = (D * B - (2 * A * E)) / (4 * A * C - B ** 2)')
    # Centers are obtained by solving for where the gradient of the quadratic
    # becomes 0. Without going through the derivation the calculation is...
    # These should be 0, 0 if we are at the origin, or our original x, y
    # coordinate specified by the keypoints. I'm doing the calculation just for
    # shits and giggles
    x_center = (B * E - (2 * C * D)) / (4 * A * C - B ** 2)
    y_center = (D * B - (2 * A * E)) / (4 * A * C - B ** 2)
    util.horiz_print('x_center = ', x_center)
    util.horiz_print('y_center = ', y_center)

    #-----------------------
    # MAJOR AND MINOR AXES
    #-----------------------
    # Now we are going to determine the major and minor axis
    # of this beast. It just the center augmented by the eigenvecs
    print('----------------------------------')

    # The angle between the major axis and our x axis is:
    l1, l2, v1, v2 = _2x2_eig(A_33)
    x_axis = np.array([1, 0])
    theta = np.arccos(x_axis.dot(v1))

    # The eccentricity is determined by:
    nu = 1
    numer  = 2 * np.sqrt((A - C) ** 2 + B ** 2)
    denom  = nu * (A + C) + np.sqrt((A - C) ** 2 + B ** 2)
    eccentricity = np.sqrt(numer / denom)

    #from scipy.special import ellipeinc
    #-----------------------
    # DRAWING
    #-----------------------
    # Lets start off by drawing the ellipse that we are goign to work with
    # Create unit circle sample

    # Draw the keypoint using the tried and true df2
    # Other things should subsiquently align
    df2.draw_kpts2(np.array([(0, 0, ia11, ia21, ia22)]), ell_linewidth=4,
                   ell_color=df2.DEEP_PINK, ell_alpha=1, arrow=True, rect=True)

    # Plot ellipse points
    _plotpts(ellipse_pts1, 0, df2.YELLOW, label='invV.dot(cicrle_pts.T).T')

    # Plot ellipse axis
    # !HELP! I DO NOT KNOW WHY I HAVE TO DIVIDE, SQUARE ROOT, AND NEGATE!!!
    l1, l2, v1, v2 = _2x2_eig(A_33)
    dx1, dy1 = (v1 / np.sqrt(l1))
    dx2, dy2 = (v2 / np.sqrt(l2))
    _plotarrow(0, 0, dx1, -dy1, color=df2.ORANGE, label='ellipse axis')
    _plotarrow(0, 0, dx2, -dy2, color=df2.ORANGE)

    # Plot ellipse orientation
    orient_axis = invV.dot(np.eye(2))
    dx1, dx2, dy1, dy2 = orient_axis.flatten()
    _plotarrow(0, 0, dx1, dy1, color=df2.BLUE, label='ellipse rotation')
    _plotarrow(0, 0, dx2, dy2, color=df2.BLUE)

    df2.legend()
    df2.dark_background()
    df2.gca().invert_yaxis()
    return locals()
    # Algebraic form of connic
    #assert (a * (x ** 2)) + (b * (x * y)) + (c * (y ** 2)) + (d * x) + (e * y) + (f) == 0


#def get_kp_border(rchip, kp):
    #np.set_printoptions(precision=8)

    #df2.reset()
    #df2.figure(9003, docla=True, doclf=True)

    #def _plotpts(data, px, color=df2.BLUE, label=''):
        ##df2.figure(9003, docla=True, pnum=(1, 1, px))
        #df2.plot2(data.T[0], data.T[1], '-', '', color=color, label=label)
        #df2.update()

    #def _plotarrow(x, y, dx, dy, color=df2.BLUE, label=''):
        #ax = df2.gca()
        #arrowargs = dict(head_width=.5, length_includes_head=True, label='')
        #arrow = df2.FancyArrow(x, y, dx, dy, **arrowargs)
        #arrow.set_edgecolor(color)
        #arrow.set_facecolor(color)
        #ax.add_patch(arrow)
        #df2.update()

    #def _2x2_eig(M2x2):
        #(evals, evecs) = np.linalg.eig(M2x2)
        #l1, l2 = evals
        #v1, v2 = evecs
        #return l1, l2, v1, v2

    ##-----------------------
    ## INPUT
    ##-----------------------
    ## We are given the keypoint in invA format
    #(x, y, ia11, ia21, ia22), ia12 = kp, 0

    ## invA2x2 is a transformation from points on a unit circle to the ellipse
    #invA2x2 = np.array([[ia11, ia12],
                        #[ia21, ia22]])

    ##-----------------------
    ## DRAWING
    ##-----------------------
    ## Lets start off by drawing the ellipse that we are goign to work with
    ## Create unit circle sample
    #tau = 2 * np.pi
    #theta_list = np.linspace(0, tau, 1000)
    #cicrle_pts = np.array([(np.cos(t), np.sin(t)) for t in theta_list])
    #ellipse_pts = invA2x2.dot(cicrle_pts.T).T
    #_plotpts(ellipse_pts, 0, df2.BLACK, label='invA2x2.dot(unit_circle)')
    #l1, l2, v1, v2 = _2x2_eig(invA2x2)
    #dx1, dy1 = (v1 * l1)
    #dx2, dy2 = (v2 * l2)
    #_plotarrow(0, 0, dx1, dy1, color=df2.ORANGE, label='invA2x2 e1')
    #_plotarrow(0, 0, dx2, dy2, color=df2.RED, label='invA2x2 e2')

    ##-----------------------
    ## REPRESENTATION
    ##-----------------------
    ## A2x2 is a transformation from points on the ellipse to a unit circle
    #A2x2 = np.linalg.inv(invA2x2)

    ## Points on a matrix satisfy (x).T.dot(E2x2).dot(x) = 1
    #E2x2 = A2x2.T.dot(A2x2)

    ##Lets check our assertion: (x).T.dot(E2x2).dot(x) = 1
    #checks = [pt.T.dot(E2x2).dot(pt) for pt in ellipse_pts]
    #assert all([abs(1 - check) < 1E-11 for check in checks])

    ##-----------------------
    ## CONIC SECTIONS
    ##-----------------------
    ## All of this was from the Perdoch paper, now lets move into conic sections
    ## We will use the notation from wikipedia
    ## http://en.wikipedia.org/wiki/Conic_section
    ## http://en.wikipedia.org/wiki/Matrix_representation_of_conic_sections

    ## The matrix representation of a conic is:
    #((A,  B, B_, C), (D, E, F)) = (E2x2.flatten(), (0, 0, 1))
    #assert B == B_, 'matrix should by symmetric'

    ## A_Q is our conic section (aka ellipse matrix)
    #A_Q = np.array(((    A, B / 2, D / 2),
                    #(B / 2,     C, E / 2),
                    #(D / 2, E / 2,     F)))

    #assert np.linalg.det(A_Q) != 0, 'degenerate conic'
    ## As long as det(A_Q) is not 0 it is not degenerate and we can work with the
    ## minor 2x2 matrix

    #A_33 = np.array(((    A, B / 2),
                     #(B / 2,     C)))

    ## (det == 0)->parabola, (det < 0)->hyperbola, (det > 0)->ellipse
    #assert np.linalg.det(A_33) > 0, 'conic is not an ellipse'

    ## Centers are obtained by solving for where the gradient of the quadratic
    ## becomes 0. Without going through the derivation the calculation is...
    ## These should be 0, 0 if we are at the origin, or our original x, y
    ## coordinate specified by the keypoints. I'm doing the calculation just for
    ## shits and giggles
    #x_center = (B * E - (2 * C * D)) / (4 * A * C - B ** 2)
    #y_center = (D * B - (2 * A * E)) / (4 * A * C - B ** 2)

    ##=================
    ## DRAWING
    ##=================
    ## Now we are going to determine the major and minor axis
    ## of this beast. It just the center augmented by the eigenvecs
    #l1, l2, v1, v2 = _2x2_eig(A_33)
    #dx1, dy1 = 0 - (v1 / np.sqrt(l1))
    #dx2, dy2 = 0 - (v2 / np.sqrt(l2))
    #_plotarrow(0, 0, dx1, dy1, color=df2.BLUE)
    #_plotarrow(0, 0, dx2, dy2, color=df2.BLUE)

    ## The angle between the major axis and our x axis is:
    #x_axis = np.array([1, 0])
    #theta = np.arccos(x_axis.dot(evec1))


    ## The eccentricity is determined by:
    #nu = 1
    #numer  = 2 * np.sqrt((A - C) ** 2 + B ** 2)
    #denom  = nu * (A + C) + np.sqrt((A - C) ** 2 + B ** 2)
    #eccentricity = np.sqrt(numer / denom)

    #from scipy.special import ellipeinc

    ## Algebraic form of connic
    ##assert (a * (x ** 2)) + (b * (x * y)) + (c * (y ** 2)) + (d * x) + (e * y) + (f) == 0

    ##---------------------

    #invA = np.array([[a, 0],
                     #[c, d]])

    #Ashape = np.linalg.inv(np.array([[a, 0],
                                     #[c, d]]))
    #Ashape /= np.sqrt(np.linalg.det(Ashape))

    #tau = 2 * np.pi
    #nSamples = 100
    #theta_list = np.linspace(0, tau, nSamples)

    ## Create unit circle sample
    #cicrle_pts  = np.array([(np.cos(t), np.sin(t)) for t in theta_list])
    #circle_hpts = np.hstack([cicrle_pts, np.ones((len(cicrle_pts), 1))])

    ## Transform as if the unit cirle was the warped patch
    #ashape_pts = Ashape.dot(cicrle_pts.T).T

    #inv = np.linalg.inv
    #svd = np.linalg.svd
    #U, S_, V = svd(Ashape)
    #S = np.diag(S_)
    #pxl_list3 = invA.dot(cicrle_pts[:, 0:2].T).T
    #pxl_list4 = invA.dot(ashape_pts[:, 0:2].T).T
    #pxl_list5 = invA.T.dot(cicrle_pts[:, 0:2].T).T
    #pxl_list6 = invA.T.dot(ashape_pts[:, 0:2].T).T
    #pxl_list7 = inv(V).dot(ashape_pts[:, 0:2].T).T
    #pxl_list8 = inv(U).dot(ashape_pts[:, 0:2].T).T
    #df2.draw()


    #def _plot(data, px, title=''):
        #df2.figure(9003, docla=True, pnum=(2, 4, px))
        #df2.plot2(data.T[0], data.T[1], '.', title)

    #df2.figure(9003, doclf=True)
    #_plot(cicrle_pts, 1, 'unit circle')
    #_plot(ashape_pts, 2, 'A => circle shape')
    #_plot(pxl_list3, 3)
    #_plot(pxl_list4, 4)
    #_plot(pxl_list5, 5)
    #_plot(pxl_list6, 6)
    #_plot(pxl_list7, 7)
    #_plot(pxl_list8, 8)
    #df2.draw()

    #invA = np.array([[a, 0, x],
                     #[c, d, y],
                     #[0, 0, 1]])

    #pxl_list = invA.dot(circle_hpts.T).T[:, 0:2]

    #df2.figure(9002, doclf=True)
    #df2.imshow(rchip)
    #df2.plot2(pxl_list.T[0], pxl_list.T[1], '.')
    #df2.draw()

    #vals = [cv2.getRectSubPix(rchip, (1, 1), tuple(pxl)) for pxl in pxl_list]
    #return vals