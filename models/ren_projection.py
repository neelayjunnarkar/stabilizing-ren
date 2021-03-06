import numpy as np
import cvxpy as cp
import time

def satisfy_lmi(
    variables, AG_t, BG2, CG1, eps, decay_factor,
    nonlin = False, Lambda_p = None, BG1_t = None, CG2_t = None, DG3_t = None
):
    
    X,   Y,  N11,  N12,  N21,  N22,  Lambda_c,  N12_h,  N21_h,  DK1_t,  DK3_h,  DK4_h = variables

    # Check that X is symmetric and positive definite
    if not np.allclose(X, X.T):
        print('REN proj: satisfy lmi: X not symmetric')
        return False
    try:
        np.linalg.cholesky(X)
    except:
        print('REN proj: satisfy lmi: X not PD')
        return False

    # Check that Y is positive definite
    if not np.allclose(Y, Y.T):
        print('REN proj: satisfy lmi: Y not symmetric')
        return False
    try:
        np.linalg.cholesky(Y)
    except:
        print('REN proj: satisfy lmi: Y not PD')
        return False

    # Check that the LMI is positive definite
    condition = construct_condition(variables, AG_t, BG2, CG1, decay_factor, stacker = 'numpy', \
        nonlin = nonlin, Lambda_p = Lambda_p, BG1_t = BG1_t, CG2_t = CG2_t, DG3_t = DG3_t)
    if not np.allclose(condition, condition.T):
        print('REN proj: satisfy lmi: condition not symmetric')
        return False
    try:
        np.linalg.cholesky(condition)
    except:
        # print('REN proj: satisfy lmi: condition not PD')
        return False

    # print('REN proj: satisfy lmi: curr params satisfy lmi')
    return True

def satisfy_orig_stability_cond(
    A, B, C, D, 
    state_size, plant_state_size, plant_nonlin_size, hidden_size, 
    eps, decay_factor, nonlin
):
    vP = cp.Variable((state_size + plant_state_size,
                      state_size + plant_state_size), PSD = True)
    if not nonlin:
        plant_nonlin_size = 0
    
    vLambda = cp.Variable((plant_nonlin_size + hidden_size, 
                           plant_nonlin_size + hidden_size), diag = True)

    mat1 = cp.bmat([[A.T@vP@A - decay_factor**2 * vP, A.T@vP@B],
                    [B.T@vP@A,                        B.T@vP@B]])

    mat2 = cp.bmat([[C,                                  D],
                    [np.zeros((D.shape[1], C.shape[1])), np.eye(D.shape[1])]])
    
    mat3 = cp.bmat([[vLambda, np.zeros((vLambda.shape[0], vLambda.shape[1]))],
                    [np.zeros((vLambda.shape[0], vLambda.shape[1])), -vLambda]])

    condition = mat1 + mat2.T @ mat3 @ mat2

    eps = 1e-5 if 1e-5 > eps / 100 else eps / 100
    constraints = [
        vP - eps * np.eye(vP.shape[0]) >> 0,
        vLambda  - eps * np.eye(vLambda.shape[0]) >> 0,
        condition + eps * np.eye(condition.shape[0]) << 0
    ]

    prob = cp.Problem(cp.Minimize(0), constraints)
    try:
        prob.solve(solver = cp.MOSEK)
    except:
        # print('REN proj: satisfy orig stability cond: Failed to solve checking problem')
        return False

    feas_stats = [cp.OPTIMAL, cp.UNBOUNDED, cp.OPTIMAL_INACCURATE, cp.UNBOUNDED_INACCURATE]
    if prob.status not in feas_stats:
        # print('REN proj: failed satisfy orig stability cond: ', prob.status)
        return False

    # Check P and Lambda are positive definite
    try:
        P = vP.value
        Lambda = vLambda.value.toarray()
    except:
        # print('REN proj: satisfy orig stability cond: could not get value of P or Lambda')
        return False

    if not (np.allclose(P, P.T) and np.allclose(Lambda, Lambda.T)):
        # print('REN proj: satisfy orig stability cond: P or Lambda not symmetric')
        return False
    
    try:
        np.linalg.cholesky(P)
    except:
        # print('REN proj: satisfy orig stability cond: P not PD')
        return False
    
    try:
        np.linalg.cholesky(Lambda)
    except:
        # print('REN proj: satisfy orig stability cond: Lambda not PD')
        return False

    return True


def construct_condition(
    variables, AG_t, BG2, CG1, decay_factor, stacker = 'cvxpy',
    nonlin = False, Lambda_p = None, BG1_t = None, CG2_t = None, DG3_t = None
):
    
    if stacker == 'cvxpy':
        stacker = cp.bmat
    else:
        stacker = np.bmat
    
    X,   Y,  N11,  N12,  N21,  N22,  Lambda_c,  N12_h,  N21_h,  DK1_t,  DK3_h,  DK4_h = variables

    ytpy = stacker([[Y, np.eye(Y.shape[0])], [np.eye(Y.shape[0]), X]])

    if nonlin:
        Lambda = stacker([[Lambda_p, np.zeros((Lambda_p.shape[0], Lambda_c.shape[1]))],
                          [np.zeros((Lambda_c.shape[0], Lambda_p.shape[1])), Lambda_c]])
    else:
        Lambda = Lambda_c

    block_11 = stacker([[decay_factor**2 * ytpy, np.zeros((ytpy.shape[1], Lambda.shape[0]))],
        [np.zeros((Lambda.shape[1], ytpy.shape[0])), Lambda]])

    block_22 = stacker([[ytpy, np.zeros((ytpy.shape[1], Lambda.shape[0]))],
        [np.zeros((Lambda.shape[1], ytpy.shape[0])), Lambda]])

    ytpay = stacker([[AG_t @ Y + BG2 @ N21, AG_t + BG2 @ N22 @ CG1],
        [N11, X @ AG_t + N12 @ CG1]])

    if nonlin:
        ytpb = stacker([[BG1_t, BG2 @ DK1_t],
                        [X @ BG1_t, N12_h]])
    else:
        ytpb = stacker([[BG2 @ DK1_t],
                        [N12_h]])

    if nonlin:
        lcy = stacker([[Lambda_p @ CG2_t @ Y, Lambda_p @ CG2_t],
                       [N21_h, DK4_h @ CG1]])
    else:
        lcy = stacker([[N21_h, DK4_h @ CG1]])

    if nonlin:
        ld = stacker([[Lambda_p @ DG3_t, np.zeros((Lambda_p.shape[0], DK3_h.shape[1]))],
                      [np.zeros((DK3_h.shape[0], DG3_t.shape[1])), DK3_h]])
    else:
        ld = DK3_h

    block_21 = stacker([[ytpay, ytpb],
                        [lcy,    ld ]])
    
    condition = stacker([[block_11, block_21.T],
                         [block_21, block_22]])

    return condition

# Uses Disciplined Parameterized Programming for a negligible speed up, but at least the code is cleaner.
class LinProjector:
    def __init__(self, AG, BG, CG, eps, decay_factor, state_size, hidden_size, ob_dim, ac_dim, rnn = False):
        self.ac_dim = ac_dim
        self.ob_dim = ob_dim
        self.state_size = state_size
        self.hidden_size = hidden_size
        self.plant_state_size = AG.shape[0]
        self.eps = eps
        self.decay_factor = decay_factor

        self.rnn = rnn

        self.AG = AG
        self.BG = BG
        self.CG = CG

        self.pX   = cp.Parameter((self.plant_state_size, self.plant_state_size), PSD = True)
        self.pY   = cp.Parameter((self.plant_state_size, self.plant_state_size), PSD = True)
        self.pN11 = cp.Parameter((self.plant_state_size, self.plant_state_size))
        self.pN12 = cp.Parameter((self.plant_state_size, self.ob_dim))
        self.pN21 = cp.Parameter((self.ac_dim, self.plant_state_size))
        self.pN22 = cp.Parameter((self.ac_dim, self.ob_dim))
        self.pLambda_c = cp.Parameter((self.hidden_size, self.hidden_size), diag = True)
        self.pN12_h = cp.Parameter((self.plant_state_size, self.hidden_size))
        self.pN21_h = cp.Parameter((self.hidden_size, self.plant_state_size))
        self.pDK1_t = cp.Parameter((self.ac_dim, self.hidden_size))
        if self.rnn:
            self.pDK3_h = np.zeros((self.hidden_size, self.hidden_size))
        else:
            self.pDK3_h = cp.Parameter((self.hidden_size, self.hidden_size))
        self.pDK4_h = cp.Parameter((self.hidden_size, self.ob_dim))

        obj_params = [self.pX, self.pY, self.pN11, self.pN12, self.pN21, self.pN22, 
            self.pLambda_c, self.pN12_h, self.pN21_h, self.pDK1_t, self.pDK3_h, self.pDK4_h]

        self.vX = cp.Variable(self.pX.shape, PSD = True)
        self.vY = cp.Variable(self.pY.shape, PSD = True)
        self.vN11 = cp.Variable(self.pN11.shape)
        self.vN12 = cp.Variable(self.pN12.shape)
        self.vN21 = cp.Variable(self.pN21.shape)
        self.vN22 = cp.Variable(self.pN22.shape)
        self.vLambda_c = cp.Variable(self.pLambda_c.shape, diag = True)
        self.vN12_h = cp.Variable(self.pN12_h.shape)
        self.vN21_h = cp.Variable(self.pN21_h.shape)
        self.vDK1_t = cp.Variable(self.pDK1_t.shape)
        if self.rnn:
            self.vDK3_h = self.pDK3_h
        else:
            self.vDK3_h = cp.Variable(self.pDK3_h.shape)
        self.vDK4_h = cp.Variable(self.pDK4_h.shape)

        variables = [self.vX, self.vY, self.vN11, self.vN12, self.vN21, self.vN22, 
            self.vLambda_c, self.vN12_h, self.vN21_h, self.vDK1_t, self.vDK3_h, self.vDK4_h]
        
        condition = construct_condition(variables, self.AG, self.BG, self.CG, self.decay_factor)

        constraints = [
            self.vLambda_c >> 0,
            condition - self.eps*np.eye(condition.shape[0]) >> 0 # LMI condition holds
        ]

        obj = sum([cp.sum_squares(pVar - vVar) for (pVar, vVar) in zip(obj_params, variables)])

        self.prob = cp.Problem(cp.Minimize(obj), constraints)

    def project(self, X, Y, N11, N12, N21, N22, Lambda_c, N12_h, N21_h, DK1_t, DK3_h, DK4_h):
        if self.rnn:
            DK3_h = self.pDK3_h # Zero DK3_h out

        originals = [X,   Y,  N11,  N12,  N21,  N22,  Lambda_c,  N12_h,  N21_h,  DK1_t,  DK3_h,  DK4_h]
        if satisfy_lmi(originals, self.AG, self.BG, self.CG, self.eps, self.decay_factor):
            print(f'REN Lin Projection: DK3_t max sing val (sat cond): {np.linalg.norm(np.linalg.inv(Lambda_c) @ DK3_h, 2)}')
            return [None for _ in originals]

        self.pX.value = X
        self.pY.value = Y
        self.pN11.value = N11
        self.pN12.value = N12
        self.pN21.value = N21
        self.pN22.value = N22
        self.pLambda_c.value = Lambda_c
        self.pN12_h.value = N12_h
        self.pN21_h.value = N21_h
        self.pDK1_t.value = DK1_t
        if not self.rnn:
            self.pDK3_h.value = DK3_h
        self.pDK4_h.value = DK4_h

        # t0 = time.time()
        self.prob.solve(solver = cp.MOSEK)
        # tf = time.time()
        # print('Lin Projection: Objective value: ', self.prob.value)
        # print('Lin Projection: Computed in: ', tf - t0, 'seconds')

        oX   = self.vX.value
        oY   = self.vY.value
        oN11 = self.vN11.value
        oN12 = self.vN12.value
        oN21 = self.vN21.value
        oN22 = self.vN22.value
        oLambda_c = self.vLambda_c.value.toarray() # Needs 'toarray' since is a sparse matrix (because diagonal
        oN12_h  = self.vN12_h.value
        oN21_h  = self.vN21_h.value
        oDK1_t  = self.vDK1_t.value
        if self.rnn:
            oDK3_h = self.vDK3_h
        else:
            oDK3_h  = self.vDK3_h.value
        oDK4_h  = self.vDK4_h.value

        if self.rnn:
            assert np.allclose(oDK3_h, np.zeros_like(oDK3_h)), "RNN Lin Projection: Output DK3_h is nonzero"
        else:
            print(f'REN Lin Projection: DK3_t max sing val: {np.linalg.norm(np.linalg.inv(Lambda_c) @ DK3_h, 2)} to {np.linalg.norm(np.linalg.inv(oLambda_c) @ oDK3_h, 2)}')

        return oX, oY, oN11, oN12, oN21, oN22, oLambda_c, oN12_h, oN21_h, oDK1_t, oDK3_h, oDK4_h

    def satisfy_orig_stability_cond(self, theta_t):
        # Check if a particular theta_t stabilizes the feedback loop
        AK_t, BK1_t, BK2_t, CK1_t, DK1_t, DK2_t, CK2_t, DK3_t, DK4_t = theta_t

        A = np.bmat([[self.AG + self.BG@DK2_t@self.CG, self.BG@CK1_t],
                     [BK2_t@self.CG,                   AK_t]])

        B = np.bmat([[self.BG@DK1_t],
                     [BK1_t]])

        C = np.bmat([[DK4_t@self.CG, CK2_t]])

        D = DK3_t

        return satisfy_orig_stability_cond(
            A, B, C, D,
            self.state_size, self.plant_state_size, 0, self.hidden_size,
            self.eps, self.decay_factor, nonlin = False
        )

class NonlinProjector:
    def __init__(
        self, AG_t, BG1_t, BG2, CG1, CG2_t, DG3_t,
        eps, decay_factor,
        state_size, hidden_size, ob_dim, ac_dim,
        rnn = False, recenter_lambda_p = True
    ):
        self.ac_dim = ac_dim
        self.ob_dim = ob_dim
        self.state_size = state_size
        self.hidden_size = hidden_size
        self.plant_state_size = AG_t.shape[0]
        self.plant_nonlin_size = CG2_t.shape[0]
        self.eps = eps
        self.decay_factor = decay_factor

        self.rnn = rnn
        self.name_str = 'RNN' if self.rnn else 'REN'
        self.recenter_lambda_p = recenter_lambda_p

        self.AG_t = AG_t
        self.BG1_t = BG1_t
        self.BG2 = BG2
        self.CG1 = CG1
        self.CG2_t = CG2_t
        self.DG3_t = DG3_t

        # Setting up problem 1 to project theta hat

        self.pX   = cp.Parameter((self.plant_state_size, self.plant_state_size), PSD = True)
        self.pY   = cp.Parameter((self.plant_state_size, self.plant_state_size), PSD = True)
        self.pN11 = cp.Parameter((self.plant_state_size, self.plant_state_size))
        self.pN12 = cp.Parameter((self.plant_state_size, self.ob_dim))
        self.pN21 = cp.Parameter((self.ac_dim, self.plant_state_size))
        self.pN22 = cp.Parameter((self.ac_dim, self.ob_dim))
        self.pLambda_p = cp.Parameter((self.plant_nonlin_size, self.plant_nonlin_size), diag = True)
        self.pLambda_c = cp.Parameter((self.hidden_size, self.hidden_size), diag = True)
        self.pN12_h = cp.Parameter((self.plant_state_size, self.hidden_size))
        self.pN21_h = cp.Parameter((self.hidden_size, self.plant_state_size))
        self.pDK1_t = cp.Parameter((self.ac_dim, self.hidden_size))
        if self.rnn:
            self.pDK3_h = np.zeros((self.hidden_size, self.hidden_size))
        else:
            self.pDK3_h = cp.Parameter((self.hidden_size, self.hidden_size))
        self.pDK4_h = cp.Parameter((self.hidden_size, self.ob_dim))

        obj_params = [self.pX, self.pY, self.pN11, self.pN12, self.pN21, self.pN22, 
            self.pLambda_c, self.pN12_h, self.pN21_h, self.pDK1_t, self.pDK3_h, self.pDK4_h]

        self.vX = cp.Variable(self.pX.shape, PSD = True)
        self.vY = cp.Variable(self.pY.shape, PSD = True)
        self.vN11 = cp.Variable(self.pN11.shape)
        self.vN12 = cp.Variable(self.pN12.shape)
        self.vN21 = cp.Variable(self.pN21.shape)
        self.vN22 = cp.Variable(self.pN22.shape)
        self.vLambda_c = cp.Variable(self.pLambda_c.shape, diag = True)
        self.vN12_h = cp.Variable(self.pN12_h.shape)
        self.vN21_h = cp.Variable(self.pN21_h.shape)
        self.vDK1_t = cp.Variable(self.pDK1_t.shape)
        if self.rnn:
            self.vDK3_h = np.zeros_like(self.pDK3_h)
        else:
            self.vDK3_h = cp.Variable(self.pDK3_h.shape)
        self.vDK4_h = cp.Variable(self.pDK4_h.shape)

        variables = [self.vX, self.vY, self.vN11, self.vN12, self.vN21, self.vN22, 
            self.vLambda_c, self.vN12_h, self.vN21_h, self.vDK1_t, self.vDK3_h, self.vDK4_h]

        condition = construct_condition(
            variables, self.AG_t, self.BG2, self.CG1, self.decay_factor,
            nonlin = True, Lambda_p = self.pLambda_p,
            BG1_t = self.BG1_t, CG2_t = self.CG2_t, DG3_t = self.DG3_t
        )

        constraints = [
            self.vLambda_c >> 0,
            condition - self.eps * np.eye(condition.shape[0]) >> 0
        ]

        obj = sum([cp.sum_squares(var - vVar) for (var, vVar) in zip(obj_params, variables)])
        self.prob1 = cp.Problem(cp.Minimize(obj), constraints)

        # Setting up the second problem to recenter Lambda_p
        if self.recenter_lambda_p:
            self.vLambda_p = cp.Variable(self.pLambda_p.shape, diag = True)
            self.vEps = cp.Variable(nonneg = True)

            condition2 = construct_condition(
                obj_params, self.AG_t, self.BG2, self.CG1, self.decay_factor,
                nonlin = True, Lambda_p = self.vLambda_p,
                BG1_t = self.BG1_t, CG2_t = self.CG2_t, DG3_t = self.DG3_t
            )
            constraints2 = [
                self.vEps >= 0.9*self.eps,
                self.vLambda_p >> 0,
                condition2 - self.vEps * np.eye(condition2.shape[0]) >> 0
            ]
            self.prob2 = cp.Problem(cp.Maximize(self.vEps), constraints2)

        # Initial Lambda_p value
        
        self.pLambda_p.value = np.eye(self.pLambda_p.shape[0])

    def project(self, X, Y, N11, N12, N21, N22, Lambda_c, N12_h, N21_h, DK1_t, DK3_h, DK4_h):
        if self.rnn:
            DK3_h = self.pDK3_h # Zero DK3_h out
        
        # Check if input theta hat parameters are already within stabilizing set
        originals = [X,   Y,  N11,  N12,  N21,  N22,  Lambda_c,  N12_h,  N21_h,  DK1_t,  DK3_h,  DK4_h]
        if satisfy_lmi(originals, self.AG_t, self.BG2, self.CG1, self.eps, self.decay_factor,
            nonlin = True, Lambda_p = self.pLambda_p.value,
            BG1_t=self.BG1_t, CG2_t=self.CG2_t, DG3_t=self.DG3_t
        ):
            print(f'{self.name_str} Nonlin Projection: DK3_t max sing val (sat cond): {np.linalg.norm(np.linalg.inv(Lambda_c) @ DK3_h, 2)}')
            return [None for _ in originals]

        # Project theta hat to stabilizing set.
        self.pX.value = X
        self.pY.value = Y
        self.pN11.value = N11
        self.pN12.value = N12
        self.pN21.value = N21
        self.pN22.value = N22
        self.pLambda_c.value = Lambda_c
        self.pN12_h.value = N12_h
        self.pN21_h.value = N21_h
        self.pDK1_t.value = DK1_t
        if not self.rnn:
            self.pDK3_h.value = DK3_h
        self.pDK4_h.value = DK4_h

        try:
            # t0 = time.time()
            print(f"{self.name_str} Projection Nonlin Prob 1: Starting solve")
            self.prob1.solve(solver = cp.MOSEK)
            # tf = time.time()
            # print('Nonlin Projection: Objective value: ', self.prob1.value)
            # print('Nonlin Projection: Computed in: ', tf - t0, 'seconds')
        except:
            assert f"{self.name_str} Projection Nonlin Prob 1: Failed to solve"
        
        feas_stats = [cp.OPTIMAL, cp.UNBOUNDED, cp.OPTIMAL_INACCURATE, cp.UNBOUNDED_INACCURATE]
        assert self.prob1.status in feas_stats, f"{self.name_str} Projection Nonlin Prob 1: infeasible"

        oX   = self.vX.value
        oY   = self.vY.value
        oN11 = self.vN11.value
        oN12 = self.vN12.value
        oN21 = self.vN21.value
        oN22 = self.vN22.value
        oLambda_c = self.vLambda_c.value.toarray() # Needs 'toarray' since is a sparse matrix (because diagonal)
        oN12_h  = self.vN12_h.value
        oN21_h  = self.vN21_h.value
        oDK1_t  = self.vDK1_t.value
        if self.rnn:
            oDK3_h = self.vDK3_h
        else:
            oDK3_h  = self.vDK3_h.value
        oDK4_h  = self.vDK4_h.value

        # Re-center Lambda p
        if self.recenter_lambda_p:
            self.pX.value   = self.vX.value
            self.pY.value   = self.vY.value
            self.pN11.value = self.vN11.value
            self.pN12.value = self.vN12.value
            self.pN21.value = self.vN21.value
            self.pN22.value = self.vN22.value
            self.pLambda_c.value = self.vLambda_c.value.toarray()
            self.pN12_h.value  = self.vN12_h.value
            self.pN21_h.value  = self.vN21_h.value
            self.pDK1_t.value  = self.vDK1_t.value
            if not self.rnn:
                self.pDK3_h.value = self.vDK3_h.value
            self.pDK4_h.value  = self.vDK4_h.value

            try:
                # t0 = time.time()
                self.prob2.solve(solver = cp.MOSEK)
                # tf = time.time()
                # print('RNN Nonlin Update LambdaP Projection: Objective value: ', self.prob2.value)
                # print('RNN Nonlin Update LambdaP Projection: Computed in: ', tf - t0, 'seconds')
            except:
                assert f"{self.name_str} Projection Nonlin LambdaP Prob: Failed to solve"

            self.pLambda_p.value = self.vLambda_p.value.toarray()
            print(f'{self.name_str} Nonlin Update LambdaP Projection: Used eps = {self.vEps.value}')

        # print('RNN Nonlin Projection: Lambda P', self.pLambda_p.value)
        print(f'{self.name_str} Nonlin Projection: DK3_t max sing val: {np.linalg.norm(np.linalg.inv(Lambda_c) @ DK3_h, 2)} to {np.linalg.norm(np.linalg.inv(oLambda_c) @ oDK3_h, 2)}')

        t0 = time.time()
        assert satisfy_lmi([oX, oY, oN11, oN12, oN21, oN22, oLambda_c, oN12_h, oN21_h, oDK1_t, oDK3_h, oDK4_h], self.AG_t, self.BG2, self.CG1, self.eps, self.decay_factor,
            nonlin = True, Lambda_p = self.pLambda_p.value,
            BG1_t=self.BG1_t, CG2_t=self.CG2_t, DG3_t=self.DG3_t), "Output does not satisfy LMI"
        tf = time.time()
        # print(f'Checking result took {tf-t0} seconds')
        return oX, oY, oN11, oN12, oN21, oN22, oLambda_c, oN12_h, oN21_h, oDK1_t, oDK3_h, oDK4_h

    def satisfy_orig_stability_cond(self, theta_t):
        # Check if a particular theta_t stabilizes the feedback loop
        AK_t, BK1_t, BK2_t, CK1_t, DK1_t, DK2_t, CK2_t, DK3_t, DK4_t = theta_t

        A = np.bmat([[self.AG_t + self.BG2@DK2_t@self.CG1, self.BG2@CK1_t],
                     [BK2_t@self.CG1,                      AK_t]])

        B = np.bmat([[self.BG1_t,                                      self.BG2@DK1_t],
                     [np.zeros((BK1_t.shape[0], self.BG1_t.shape[1])), BK1_t]])

        C = np.bmat([[self.CG2_t,     np.zeros((self.CG2_t.shape[0], CK2_t.shape[1]))],
                     [DK4_t@self.CG1, CK2_t]])

        D = np.bmat([[self.DG3_t, np.zeros((self.DG3_t.shape[0], DK3_t.shape[1]))],
                     [np.zeros((DK3_t.shape[0], self.DG3_t.shape[1])), DK3_t]])

        return satisfy_orig_stability_cond(
            A, B, C, D,
            self.state_size, self.plant_state_size, self.plant_nonlin_size, self.hidden_size,
            self.eps, self.decay_factor, nonlin = True
        )
