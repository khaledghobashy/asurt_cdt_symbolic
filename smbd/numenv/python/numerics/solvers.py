# -*- coding: utf-8 -*-
"""
Created on Tue Jan  1 13:21:35 2019

@author: khale
"""

import sys
import numpy as np
import scipy as sc
import scipy.integrate
from scipy.sparse.linalg import spsolve
import pandas as pd

def solve(A,b):
    try:
        A = A.A
    except AttributeError:
        pass
    x = np.linalg.solve(A,b)
    shape = (x.shape[0],x.size//x.shape[0])
    x = np.reshape(x,shape)
    return x

def progress_bar(steps, i):
    sys.stdout.write('\r')
    length=(100*(1+i)//(4*steps))
    percentage=100*(1+i)//steps
#    sys.stdout.write("Progress: ")
    sys.stdout.write("[%-25s] %d%%, (%s/%s) steps." % ('='*length,percentage,i+1, steps))
    sys.stdout.flush()

def scipy_matrix_assembler(data, rows, cols, shape):
    mat = sc.empty(shape, dtype=np.object)
    mat[rows, cols] = data
    return sc.sparse.bmat(mat, format='csc')

###############################################################################
###############################################################################

class abstract_solver(object):
    
    def __init__(self, model):
        self.model = model
        model.initialize()
        q0 = model.q0
        model.set_gen_coordinates(q0)
        
        self._nrows = model.nrows
        self._ncols = model.ncols
        self._jac_shape = (self._nrows,self._ncols)
        
        self._pos_history = {0: q0}
        self._vel_history = {0: np.zeros_like(q0)}
        self._acc_history = {}
        
        sorted_coordinates = {v:k for k,v in model.indicies_map.items()}
        self._coordinates_indicies = []
        for name in sorted_coordinates.values():
            self._coordinates_indicies += ['%s.%s'%(name, i) 
            for i in ['x', 'y', 'z', 'e0', 'e1', 'e2', 'e3']]
            
        self._reactions_indicies = []
        for name in model.reactions_indicies:
            self._reactions_indicies += ['%s.%s'%(name, i) 
            for i in ['x','y','z']]
    
    def set_time_array(self, duration, spacing):
        
        if duration > spacing:
            time_array = np.arange(0, duration, spacing)
            step_size  = spacing
        elif duration < spacing:
            time_array, step_size = np.linspace(0, duration, spacing, retstep=True)
        else:
            raise ValueError('Time array is not properly sampled.')
        self.time_array = time_array
        self.step_size  = step_size
        
    def eval_reactions(self):
        self._reactions = {}
        time_array = self.time_array
        bar_length = len(time_array)
        print('\nEvaluating System Constraints Reactions:')
        for i, t in enumerate(time_array):
            progress_bar(bar_length, i)
            self._set_time(t)
            lamda = self._eval_lagrange_multipliers(i)
            self._eval_reactions_eq(lamda)
            self._reactions[i] = self.model.reactions
        
        self.values = {i:np.concatenate(list(v.values())) for i,v in self._reactions.items()}
        
        self.reactions_dataframe = pd.DataFrame(
                data = np.concatenate(list(self.values.values()),1).T,
                columns = self._reactions_indicies)
        self.reactions_dataframe['time'] = time_array
    
    def _initialize_model(self):
        model = self.model
        model.initialize()
        q0 = model.q0
        model.set_gen_coordinates(q0)
    
    def _creat_results_dataframes(self):
        columns = self._coordinates_indicies
        
        self.pos_dataframe = pd.DataFrame(
                data = np.concatenate(list(self._pos_history.values()),1).T,
                columns = columns)
        self.vel_dataframe = pd.DataFrame(
                data = np.concatenate(list(self._vel_history.values()),1).T,
                columns = columns)
        self.acc_dataframe = pd.DataFrame(
                data = np.concatenate(list(self._acc_history.values()),1).T,
                columns = columns)
        
        time_array = self.time_array
        self.pos_dataframe['time'] = time_array
        self.vel_dataframe['time'] = time_array
        self.acc_dataframe['time'] = time_array
    
    def _assemble_equations(self, data):
        mat = np.concatenate(data)
        return mat
    
    def _set_time(self, t):
        self.model.t = t
    
    def _set_gen_coordinates(self, q):
        self.model.set_gen_coordinates(q)
    
    def _set_gen_velocities(self, qd):
        self.model.set_gen_velocities(qd)
    
    def _set_gen_accelerations(self, qdd):
        self.model.set_gen_accelerations(qdd)
    
    def _eval_pos_eq(self):
        self.model.eval_pos_eq()
        data = self.model.pos_eq_blocks
        mat = self._assemble_equations(data)
        return mat
        
    def _eval_vel_eq(self):
        self.model.eval_vel_eq()
        data = self.model.vel_eq_blocks
        mat = self._assemble_equations(data)
        return mat
        
    def _eval_acc_eq(self):
        self.model.eval_acc_eq()
        data = self.model.acc_eq_blocks
        mat = self._assemble_equations(data)
        return mat
            
    def _eval_jac_eq(self):
        self.model.eval_jac_eq()
        rows = self.model.jac_rows
        cols = self.model.jac_cols
        data = self.model.jac_eq_blocks
        mat = scipy_matrix_assembler(data, rows, cols, self._jac_shape)
        return mat
    
    def _eval_mass_eq(self):
        self.model.eval_mass_eq()
        data = self.model.mass_eq_blocks
        n = self.model.ncols
        rows = cols = np.arange(n)
        mat = scipy_matrix_assembler(data, rows, cols, (n,n))
        return mat.A
    
    def _eval_frc_eq(self):
        self.model.eval_frc_eq()
        data = self.model.frc_eq_blocks
        mat = self._assemble_equations(data)
        return mat
        
    def _eval_reactions_eq(self, lamda):
        self.model.set_lagrange_multipliers(lamda)
        self.model.eval_reactions_eq()
    
    def _newton_raphson(self, guess):
        self._set_gen_coordinates(guess)
        
        A = self._eval_jac_eq()
        b = self._eval_pos_eq()
        delta_q = solve(A, -b)
        
        itr=0
        while np.linalg.norm(delta_q)>1e-5:
#            print(np.linalg.norm(delta_q))
            guess = guess + delta_q
            
            self._set_gen_coordinates(guess)
            b = self._eval_pos_eq()
            delta_q = solve(A, -b)
            
            if itr%5==0 and itr!=0:
                A = self._eval_jac_eq()
                delta_q = solve(A, -b)
            if itr>50:
                print("Iterations exceded \n")
                break
            itr+=1
        self.pos = guess

###############################################################################
###############################################################################

class kds_solver(abstract_solver):
    
    def solve(self, run_id):
        self._initialize_model()
        time_array = self.time_array
        dt = self.step_size
        
        A = self._eval_jac_eq()
        vel_rhs = self._eval_vel_eq()
        v0 = solve(A, -vel_rhs)
        self._set_gen_velocities(v0)
        self._vel_history[0] = v0
        
        acc_rhs = self._eval_acc_eq()
        self._acc_history[0] = solve(A, -acc_rhs)
        
        print('\nRunning System Kinematic Analysis:')
        bar_length = len(time_array)-1
        for i,t in enumerate(time_array[1:]):
            progress_bar(bar_length, i)
            self._set_time(t)

            g =   self._pos_history[i] \
                + self._vel_history[i]*dt \
                + 0.5*self._acc_history[i]*(dt**2)
            
            self._newton_raphson(g)
            self._pos_history[i+1] = self.pos
            A = self._eval_jac_eq()
            
            vel_rhs = self._eval_vel_eq()
            vi = solve(A,-vel_rhs)
            self._set_gen_velocities(vi)
            self._vel_history[i+1] = vi

            acc_rhs = self._eval_acc_eq()
            self._acc_history[i+1] = solve(A,-acc_rhs)
        
        print('\n')
        self._creat_results_dataframes()    
    
    def _eval_lagrange_multipliers(self, i):
        self._set_gen_coordinates(self._pos_history[i])
        self._set_gen_velocities(self._vel_history[i])
        self._set_gen_accelerations(self._acc_history[i])
        
        applied_forces = self._eval_frc_eq()
        mass_matrix = self._eval_mass_eq()
        jac = self._eval_jac_eq()
        qdd = self._acc_history[i]
        inertia_forces = mass_matrix.dot(qdd)
        rhs = applied_forces - inertia_forces
        lamda = solve(jac.T, rhs)
        
        return lamda

###############################################################################
###############################################################################

class dds_solver(abstract_solver):
    
    def solve(self, run_id):
        self._initialize_model()
        time_array = self.time_array
        dt = self.step_size
        bar_length = len(time_array)-1
        print('\nStarting System Dynamic Analysis:')
        
        self._extract_independent_coordinates()
        print('Estimated DOF : %s'%(len(self.independent_cord),))
        print('Estimated Independent Coordinates : %s'%(self.independent_cord,))
        
        pos_t0 = self._pos_history[0]
        vel_t0 = self._vel_history[0]
        self._get_initial_conditions(pos_t0, vel_t0)
        
        integrator = scipy.integrate.ode(self._state_space_model)
        integrator.set_integrator('lsoda')
        integrator.set_initial_value(self.y0)
        
        M, J, Qt, Qd = self._eval_augmented_matricies(pos_t0, vel_t0)
        acc_t0, lamda_t0 = self._solve_augmented_system(M, J, Qt, Qd)
        M_hat, Q_hat = self._partioned_system(M, J, Qt, Qd)
        integrator.set_f_params(M_hat, Q_hat)
        
        self._acc_history[0] = acc_t0
        
        print('\nRunning System Dynamic Analysis:')
        for i,t in enumerate(time_array[1:]):
            progress_bar(bar_length,i)
            self._set_time(t)
                
            integrator.integrate(t)
            yi = integrator.y
            
            ind_pos_i = yi[:len(yi)//2]
            ind_vel_i = yi[len(yi)//2:]
            
#            print('time : %s'%integrator.t)
#            print(dict(zip(self.independent_cord,list(ind_pos_i[:,0]))))
#            print(dict(zip(self.independent_cord,list(ind_vel_i[:,0]))))
#            print('\n')

            g = self._pos_history[i] \
                + self._vel_history[i]*dt \
                + 0.5*self._acc_history[i]*(dt**2)
            
            for c in range(self.dof): 
                g[np.argmax(self.independent_cols[:,c]),0] = ind_pos_i[c]
            
            self._newton_raphson(g)
            self._pos_history[i+1] = self.pos
            
#            vi = self._solve_velocity(ind_vel_i)
#            self._vel_history[i+1] = vi
            
            A = self._eval_jac_eq()
            vel_rhs = self._eval_vel_eq(ind_vel_i)
            vi = solve(A,-vel_rhs)
            self._vel_history[i+1] = vi

            M, J, Qt, Qd = self._eval_augmented_matricies(self.pos, vi)
            
            acc_ti, lamda_ti = self._solve_augmented_system(M, J, Qt, Qd)
            self._acc_history[i+1] = acc_ti            
            
            M_hat, Q_hat = self._partioned_system(M, J, Qt, Qd)
            integrator.set_f_params(M_hat, Q_hat)
        
        print('\n')
        self._creat_results_dataframes()

    def _solve_velocity(self,vdot):
        dof = self.dof
        P = self.permutaion_mat
        J = super()._eval_jac_eq(self).A
        Jp = J@P.T
        Jv = Jp[:,-dof:]
        Ju = Jp[:,:-dof]
        H = -solve(Ju, Jv)
        udot = H@vdot
        qd = np.concatenate([udot,vdot])
        return P.T@qd
    
    
    def _extract_independent_coordinates(self):
        A = super()._eval_jac_eq()
        rows, cols = A.shape
        permutaion_mat = sc.linalg.lu(A.A.T)[0]
        independent_cols = permutaion_mat[:, rows:]
        self.dof = dof = independent_cols.shape[1]
        independent_cord = [self._coordinates_indicies[np.argmax(independent_cols[:,i])] for i in range(dof) ]
        self.permutaion_mat  = permutaion_mat.T
        self.independent_cols = independent_cols
        self.independent_cord = independent_cord
    
    def _get_initial_conditions(self,pos_t0, vel_t0):
        cols = self.independent_cols
        dof  = self.dof
        initial_pos = [pos_t0[np.argmax(cols[:,i])] for i in range(dof)]
        initial_vel = [vel_t0[np.argmax(cols[:,i])] for i in range(dof)]
        self.y0 =  initial_pos + initial_vel
    
    
    def _eval_augmented_matricies(self,q ,qd):
        self._set_gen_coordinates(q)
        self._set_gen_velocities(qd)
        J  = super()._eval_jac_eq().A
        M  = self._eval_mass_eq()
        Qt = self._eval_frc_eq()
        Qd = self._eval_acc_eq()
        return M, J, Qt, Qd
    
    def _solve_augmented_system(self, M, J, Qt, Qd):        
        A = sc.sparse.bmat([[M,J.T],[J,None]], format='csc')
        b = np.concatenate([Qt,-Qd])
        x = solve(A, b)
        n = len(self._coordinates_indicies)
        accelerations = x[:n]
        lamda = x[n:]
        return accelerations, lamda
    
    def _eval_pos_eq(self):
        A = super()._eval_pos_eq()
        Z = np.zeros((self.dof,1))
        A = np.concatenate([A,Z])
        return A

    def _eval_vel_eq(self,ind_vel_i):
        A = super()._eval_vel_eq()
        V = np.array(ind_vel_i)
        V = np.reshape(V,(self.dof,1))
        A = np.concatenate([A,-V])
        return A
    
    def _eval_jac_eq(self):
        A = super()._eval_jac_eq()
        A = A.A
        A = np.concatenate([A,self.independent_cols.T])
        return sc.sparse.csc_matrix(A)
    
        
    def _partioned_system(self, M, J, Q, acc_rhs):
        P   = self.permutaion_mat
        dof = self.dof
        
        Mp = P @ M @ P.T
        Qp = P@Q
        Jp = J@P.T
        
        Jv = Jp[:,-dof:]
        Ju = Jp[:,:-dof]
        
        H = -solve(Ju, Jv)

        Mvv = Mp[-dof:, -dof:]
        Mvu = Mp[-dof:, :-dof]
        Muu = Mp[:-dof, :-dof]
        Muv = Mp[:-dof, -dof:]
        
        Qv = Qp[-dof:]
        Qu = Qp[:-dof]
        
        M_hat = Mvv + (Mvu @ H) + H.T@(Muv + Muu@H)
        Q_hat = Qv + H.T@Qu - (Mvu + H.T@Muu)@solve(Ju,-acc_rhs)
        
        return M_hat, Q_hat

    @staticmethod
    def _state_space_model(t, y, M_hat, Q_hat):
#        print('IN SSODE : ')
        v = list(y[len(y)//2:])
        vdot = list(solve(sc.sparse.csc_matrix(M_hat), Q_hat))
        dydt = v + vdot
        return dydt
