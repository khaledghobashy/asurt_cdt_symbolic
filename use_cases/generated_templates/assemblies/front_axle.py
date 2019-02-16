
import numpy as np

from use_cases.generated_templates.configurations import dwb_simple_points
from use_cases.generated_templates.configurations import steer_simple_points

from use_cases.generated_templates.templates import dwb
from use_cases.generated_templates.templates import steer
from use_cases.generated_templates.templates import test_rig

SU = dwb.topology('SU',dwb_simple_points.configuration())

ST = steer.topology('ST',steer_simple_points.configuration())

TR = test_rig.topology('TR')



class numerical_assembly(object):

    def __init__(self):
        self._t = 0
        self.subsystems = [SU,ST,TR]

        self.interface_map = {'SU.vbs_ground': 'ground', 'SU.vbl_steer': 'ST.rbl_rocker', 'SU.vbs_chassis': 'ground', 'SU.vbr_steer': 'ST.rbr_rocker', 'ST.vbs_ground': 'ground', 'ST.vbs_chassis': 'ground', 'TR.vbr_upright': 'SU.rbr_upright', 'TR.vbl_upright': 'SU.rbl_upright', 'TR.vbl_hub': 'SU.rbl_hub', 'TR.vbr_hub': 'SU.rbr_hub', 'TR.vbs_chassis': 'ground', 'TR.vbs_ground': 'ground', 'TR.vbs_steer_gear': 'ST.rbr_rocker'}
        self.indicies_map  = {'ground': 0, 'SU.rbr_uca': 1, 'SU.rbl_uca': 2, 'SU.rbr_lca': 3, 'SU.rbl_lca': 4, 'SU.rbr_upright': 5, 'SU.rbl_upright': 6, 'SU.rbr_upper_strut': 7, 'SU.rbl_upper_strut': 8, 'SU.rbr_lower_strut': 9, 'SU.rbl_lower_strut': 10, 'SU.rbr_tie_rod': 11, 'SU.rbl_tie_rod': 12, 'SU.rbr_hub': 13, 'SU.rbl_hub': 14, 'ST.rbs_coupler': 15, 'ST.rbr_rocker': 16, 'ST.rbl_rocker': 17}

        self.R_ground  = np.array([[0],[0],[0]],dtype=np.float64)
        self.P_ground  = np.array([[1],[0],[0],[0]],dtype=np.float64)
        self.Pg_ground = np.array([[1],[0],[0],[0]],dtype=np.float64)

        self.gr_rows = np.array([0,1])
        self.gr_jac_rows = np.array([0,0,1,1])
        self.gr_jac_cols = np.array([0,1,0,1])

        self.nrows = 79
        self.ncols = 36

        self.initialize_assembly()


    @property
    def t(self):
        return self._t
    @t.setter
    def t(self,t):
        self._t = t
        for sub in self.subsystems:
            sub.t = t

    def set_initial_states(self):
        for sub in self.subsystems:
            sub.set_initial_states()
        coordinates = [sub.config.q for sub in self.subsystems if len(sub.config.q)!=0]
        self.q0 = np.concatenate([self.R_ground,self.P_ground,*coordinates])

    def initialize_assembly(self):
        self.t = 0
        self.assemble_system()
        self.set_initial_states()
        self.eval_constants()

    def assemble_system(self):
        offset = 0
        for sub in self.subsystems:
            sub.assemble_template(self.indicies_map,self.interface_map,offset)
            offset += sub.nrows

        self.gr_rows += offset
        self.gr_jac_rows += offset

        self.rows = np.concatenate([s.rows for s in self.subsystems])
        self.jac_rows = np.concatenate([s.jac_rows for s in self.subsystems])
        self.jac_cols = np.concatenate([s.jac_cols for s in self.subsystems])

        self.rows = np.concatenate([self.rows,self.gr_rows])
        self.jac_rows = np.concatenate([self.jac_rows,self.gr_jac_rows])
        self.jac_cols = np.concatenate([self.jac_cols,self.gr_jac_cols])

    
    def eval_constants(self):
        SU.config.R_vbs_ground = self.R_ground
        SU.config.P_vbs_ground = self.P_ground
        SU.config.R_vbl_steer = ST.config.R_rbl_rocker
        SU.config.P_vbl_steer = ST.config.P_rbl_rocker
        SU.config.R_vbs_chassis = self.R_ground
        SU.config.P_vbs_chassis = self.P_ground
        SU.config.R_vbr_steer = ST.config.R_rbr_rocker
        SU.config.P_vbr_steer = ST.config.P_rbr_rocker
        ST.config.R_vbs_ground = self.R_ground
        ST.config.P_vbs_ground = self.P_ground
        ST.config.R_vbs_chassis = self.R_ground
        ST.config.P_vbs_chassis = self.P_ground
        TR.config.R_vbr_upright = SU.config.R_rbr_upright
        TR.config.P_vbr_upright = SU.config.P_rbr_upright
        TR.config.R_vbl_upright = SU.config.R_rbl_upright
        TR.config.P_vbl_upright = SU.config.P_rbl_upright
        TR.config.R_vbl_hub = SU.config.R_rbl_hub
        TR.config.P_vbl_hub = SU.config.P_rbl_hub
        TR.config.R_vbr_hub = SU.config.R_rbr_hub
        TR.config.P_vbr_hub = SU.config.P_rbr_hub
        TR.config.R_vbs_chassis = self.R_ground
        TR.config.P_vbs_chassis = self.P_ground
        TR.config.R_vbs_ground = self.R_ground
        TR.config.P_vbs_ground = self.P_ground
        TR.config.R_vbs_steer_gear = ST.config.R_rbr_rocker
        TR.config.P_vbs_steer_gear = ST.config.P_rbr_rocker

        for sub in self.subsystems:
            sub.eval_constants()

    
    def set_gen_coordinates(self,q):
        self.R_ground = q[0:3,0:1]
        self.P_ground = q[3:7,0:1]
        offset = 7
        for sub in self.subsystems:
            qs = q[offset:sub.n+offset]
            sub.set_gen_coordinates(qs)
            offset += sub.n

        SU.R_vbs_ground = self.R_ground
        SU.P_vbs_ground = self.P_ground
        SU.R_vbl_steer = ST.R_rbl_rocker
        SU.P_vbl_steer = ST.P_rbl_rocker
        SU.R_vbs_chassis = self.R_ground
        SU.P_vbs_chassis = self.P_ground
        SU.R_vbr_steer = ST.R_rbr_rocker
        SU.P_vbr_steer = ST.P_rbr_rocker
        ST.R_vbs_ground = self.R_ground
        ST.P_vbs_ground = self.P_ground
        ST.R_vbs_chassis = self.R_ground
        ST.P_vbs_chassis = self.P_ground
        TR.R_vbr_upright = SU.R_rbr_upright
        TR.P_vbr_upright = SU.P_rbr_upright
        TR.R_vbl_upright = SU.R_rbl_upright
        TR.P_vbl_upright = SU.P_rbl_upright
        TR.R_vbl_hub = SU.R_rbl_hub
        TR.P_vbl_hub = SU.P_rbl_hub
        TR.R_vbr_hub = SU.R_rbr_hub
        TR.P_vbr_hub = SU.P_rbr_hub
        TR.R_vbs_chassis = self.R_ground
        TR.P_vbs_chassis = self.P_ground
        TR.R_vbs_ground = self.R_ground
        TR.P_vbs_ground = self.P_ground
        TR.R_vbs_steer_gear = ST.R_rbr_rocker
        TR.P_vbs_steer_gear = ST.P_rbr_rocker

    
    def set_gen_velocities(self,qd):
        self.Rd_ground = qd[0:3,0:1]
        self.Pd_ground = qd[3:7,0:1]
        offset = 7
        for sub in self.subsystems:
            qs = qd[offset:sub.n+offset]
            sub.set_gen_velocities(qs)
            offset += sub.n

        SU.Rd_vbs_ground = self.Rd_ground
        SU.Pd_vbs_ground = self.Pd_ground
        SU.Rd_vbl_steer = ST.Rd_rbl_rocker
        SU.Pd_vbl_steer = ST.Pd_rbl_rocker
        SU.Rd_vbs_chassis = self.Rd_ground
        SU.Pd_vbs_chassis = self.Pd_ground
        SU.Rd_vbr_steer = ST.Rd_rbr_rocker
        SU.Pd_vbr_steer = ST.Pd_rbr_rocker
        ST.Rd_vbs_ground = self.Rd_ground
        ST.Pd_vbs_ground = self.Pd_ground
        ST.Rd_vbs_chassis = self.Rd_ground
        ST.Pd_vbs_chassis = self.Pd_ground
        TR.Rd_vbr_upright = SU.Rd_rbr_upright
        TR.Pd_vbr_upright = SU.Pd_rbr_upright
        TR.Rd_vbl_upright = SU.Rd_rbl_upright
        TR.Pd_vbl_upright = SU.Pd_rbl_upright
        TR.Rd_vbl_hub = SU.Rd_rbl_hub
        TR.Pd_vbl_hub = SU.Pd_rbl_hub
        TR.Rd_vbr_hub = SU.Rd_rbr_hub
        TR.Pd_vbr_hub = SU.Pd_rbr_hub
        TR.Rd_vbs_chassis = self.Rd_ground
        TR.Pd_vbs_chassis = self.Pd_ground
        TR.Rd_vbs_ground = self.Rd_ground
        TR.Pd_vbs_ground = self.Pd_ground
        TR.Rd_vbs_steer_gear = ST.Rd_rbr_rocker
        TR.Pd_vbs_steer_gear = ST.Pd_rbr_rocker

    
    def eval_pos_eq(self):

        pos_ground_eq_blocks = [self.R_ground,(-1*self.Pg_ground + self.P_ground)]

        for sub in self.subsystems:
            sub.eval_pos_eq()
        self.pos_eq_blocks = sum([s.pos_eq_blocks for s in self.subsystems],[])
        self.pos_eq_blocks += pos_ground_eq_blocks

    
    def eval_vel_eq(self):

        vel_ground_eq_blocks = [np.zeros((3,1),dtype=np.float64),np.zeros((4,1),dtype=np.float64)]

        for sub in self.subsystems:
            sub.eval_vel_eq()
        self.vel_eq_blocks = sum([s.vel_eq_blocks for s in self.subsystems],[])
        self.vel_eq_blocks += vel_ground_eq_blocks

    
    def eval_acc_eq(self):

        acc_ground_eq_blocks = [np.zeros((3,1),dtype=np.float64),np.zeros((4,1),dtype=np.float64)]

        for sub in self.subsystems:
            sub.eval_acc_eq()
        self.acc_eq_blocks = sum([s.acc_eq_blocks for s in self.subsystems],[])
        self.acc_eq_blocks += acc_ground_eq_blocks

    
    def eval_jac_eq(self):

        jac_ground_eq_blocks = [np.eye(3,dtype=np.float64),np.zeros((3,4),dtype=np.float64),np.zeros((4,3),dtype=np.float64),np.eye(4,dtype=np.float64)]

        for sub in self.subsystems:
            sub.eval_jac_eq()
        self.jac_eq_blocks = sum([s.jac_eq_blocks for s in self.subsystems],[])
        self.jac_eq_blocks += jac_ground_eq_blocks
  
