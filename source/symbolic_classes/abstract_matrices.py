# -*- coding: utf-8 -*-
"""
Created on Tue Jan  1 10:47:50 2019

@author: khale
"""

import sympy as sm

import networkx as nx
import matplotlib.pyplot as plt

sm.init_printing(pretty_print=False,use_latex=True,forecolor='White')
ccode_print = False
enclose = True

class AbstractMatrix(sm.MatrixExpr):
    
    is_commutative = False
    is_Matrix = True
    shape = (3,3)
    
    def __init__(self,sym):
        pass
    
    def doit(self):
        return self
    
class A(AbstractMatrix):
    
    def _latex(self,expr):
        return '{A(%s)}'%self.args[0]


class G(AbstractMatrix):
    shape = (3,4)
    

class E(AbstractMatrix):
    shape = (3,4)
    
class B(AbstractMatrix):
    shape = (3,4)
    def __init__(self,sym1,sym2):
        super().__init__(sym1)
    
    def _latex(self,expr):
        p,u = self.args
        return '{B(%s,%s)}'%(p,u.name)
    

class Triad(AbstractMatrix):
    def __init__(self,v1,v2=None):
        super().__init__(v1)


################################################################
################################################################

class base_vector(sm.MatrixSlice):
    
    shape = (3,1)
    
    def __new__(cls,frame,sym):
        slices = {'i':(0,1),'j':(1,2),'k':(2,3)}
        return super().__new__(cls,frame.A,(0,3),slices[sym])
    
    def __init__(self,frame,sym):
        slices = {'i':(0,1),'j':(1,2),'k':(2,3)}
        self.slice = slices[sym]
        self.frame = frame
        self._sym  = sym
        self._name = '%s_%s'%(sym,frame.name)
        self._formated = '{\hat{%s}_{%s}}'%(self._sym,self.frame.name)
        self._args = (frame,sym)
    
    def express(self,frame=None):
        if frame:
            frame = frame
        else:
            frame = reference_frame._global_frame
        A = self.frame.parent.express(frame)
        return A*self
    
    def doit(self):
        return self
    
    def _latex(self,expr):
        return self._formated
    
    def _ccode(self,expr,**kwargs):
        global enclose
        if enclose:
            return '%r[:,%s:%s]'%(self.frame.name,*self.slice)
        else:
            return '%s[:,%s:%s]'%(self.frame.name,*self.slice)
    
    def _sympystr (self,expr):
        return '%s[:,%s]'%(self.frame.name,self.slice)
    
    '''def _pretty(self,expr):
        return self._formated'''
    
    @property
    def name(self):
        return '{\hat{%s}_{%s}}'%(self._sym,self.frame.name)
    
    
    '''def doit(self):
        return self.frame[:,self.slices]'''
    
    @property
    def func(self):
        return base_vector


class dcm(sm.MatrixSymbol):
    shape = (3,3)
    
    is_commutative = False
    
    def __new__(cls,name, format_as=None):
        
        if format_as:
            name = format_as
        
        return super(dcm,cls).__new__(cls,name,3,3)
    
    def __init__(self,name, frame=None, format_as=None):
        
        self._raw_name = name
        self._formated_name = super().name
        
        self._args=(self._raw_name,self._formated_name)
    
    def doit(self):
        return self
    
    @property
    def name(self):
        if ccode_print:
            return self.args[0]
        else:
            return self.args[1]
    @property
    def func(self):
        return dcm
        

class zero_matrix(sm.MatrixSymbol):
    
    def __new__(cls,m,n):
        sym = '{Z_{%sx%s}}'%(m,n)
        return super().__new__(cls,sym,m,n)
    def __init__(self,m,n):
        self.sym = super().name
        self._args = (m,n)
    
    def _latex(self,expr):
        return self.sym
    def _ccode(self,expr,**kwargs):
        return 'np.zeros((%s,%s),dtype=np.float64)'%(self.shape)
    def _sympystr(self,expr):
        return 'zero_matrix(%s,%s)'%self.shape
    
    def doit(self):
        return self
    @property
    def func(self):
        return zero_matrix
    @property
    def shape(self):
        return self._args



class reference_frame(object):
    
    reference_tree = nx.DiGraph()
    
    _global_set   = False
    _global_frame = None
    _is_global    = False
    
    @classmethod
    def _set_global_frame(cls,name):
        cls._global_set = True
        cls._global_frame  = reference_frame(name)
        cls._global_frame._is_global = True
        cls.reference_tree.add_node(cls._global_frame.name)
    @classmethod
    def show_tree(cls):
        nx.draw(cls.reference_tree,with_labels=True)
        plt.show()
    
    
    def __new__(cls, name, parent=None,format_as=None):
        if not cls._global_set:
            cls._set_global_frame('grf')
        return super(reference_frame,cls).__new__(cls)
    
    
    def __init__(self, name, parent=None,format_as=None):
        #print('Inside reference_frame()')
        self._raw_name = name
        self._formated_name = (format_as if format_as else name)
        self._key = name
    
        self.parent = (parent if parent else reference_frame._global_frame)
        
        self._A = dcm(self._raw_name,self._formated_name)
        self.i  = base_vector(self,'i')
        self.j  = base_vector(self,'j')
        self.k  = base_vector(self,'k')

        self.update_tree()
            
    def update_tree(self):
        if self.parent :
            reference_frame.reference_tree.add_edge(self.parent._key, self._key, mat=self.A.T)
            reference_frame.reference_tree.add_edge(self._key, self.parent._key, mat=self.A)
    
    @property
    def A(self):
        return self._A
    @A.setter
    def A(self,value):
        self._A = value
        self.i = base_vector(self,'i')
        self.j = base_vector(self,'j')
        self.k = base_vector(self,'k')
        self.update_tree()
    
    @property
    def name(self):
        global ccode_print
        if ccode_print:
            return self._raw_name
        else:
            return self._formated_name
    
    
    def express(self,other):
        
        child_name  = self._key
        parent_name = other._key
        graph = reference_frame.reference_tree
        
        path_nodes  = nx.algorithms.shortest_path(graph, child_name, parent_name)
        path_matrices = []
        for i in range(len(path_nodes)-1):
            path_matrices.append(graph.edges[path_nodes[-i-2],path_nodes[-i-1]]['mat'])
        
        mat = sm.MatMul(*path_matrices)
        return mat
    
    def orient_along(self,v1,v2=None):
        if v2 is None:
            self.A = Triad(v1)
        else:
            self.A = Triad(v1,v2)
    

class vector(sm.MatrixSymbol):
    shape = (3,1)
    
    is_commutative = False
    
    def __new__(cls,name, frame=None, format_as=None):
        
        if format_as:
            name = format_as
        
        return super(vector,cls).__new__(cls,name,3,1)
    
    def __init__(self,name, frame=None, format_as=None):
        
        self._raw_name = name
        self._formated_name = super().name
        
        if frame:
            self.frame = frame
        else:
            self.frame = reference_frame._global_frame
        
        self._args = (name,self.frame,self._formated_name)
    
    def express(self,frame=None):
        if frame:
            frame = frame
        else:
            frame = reference_frame._global_frame
        A = self.frame.express(frame)
        return A*self
    
    
    def doit(self):
        return self
    
    @property
    def name(self):
        if ccode_print:
            return self.args[0]
        else:
            return self.args[2]
    
    def rename(self,name,format_as=None):
        self._raw_name = name
        self._formated_name = (format_as if format_as else name)
        self._args = (name,self.frame,self._formated_name)
    


class quatrenion(sm.MatrixSymbol):
    shape = (4,1)
    
    is_commutative = False
    
    def __new__(cls, name, format_as=None):
        if format_as:
            name = format_as
        return super(quatrenion,cls).__new__(cls,name,*cls.shape)
    
    def __init__(self,name, format_as=None):
        self._raw_name = name
        self._formated_name = super().name
        
        self._args = (name,self._formated_name)
    
    def doit(self):
        return self
    
    @property
    def func(self):
        return self.__class__
        
        
    @property
    def name(self):
        if ccode_print:
            return self.args[0]
        else:
            return self.args[1]
    
    def rename(self,name,format_as=None):
        self._raw_name = name
        self._formated_name = (format_as if format_as else name)
        self._args = (name,self._formated_name)

    


class abstract_mbs(object):
    
    
    def configuration_constants(self):
        from source.symbolic_classes.bodies import body
        from source.symbolic_classes.algebraic_constraints import algebraic_constraints as algebraic_constraints
        if isinstance(self,body):
            return []
        elif isinstance(self,algebraic_constraints):
            loc  = vector('pt_%s'%self.name)
            axis = vector('ax_%s'%self.name)

            ui_bar_eq = sm.Eq(self.ui_bar, loc.express(self.body_i) - self.Ri.express(self.body_i))
            uj_bar_eq = sm.Eq(self.uj_bar, loc.express(self.body_j) - self.Rj.express(self.body_j))

            marker = reference_frame('M_%s'%self.name,format_as=r'{{M}_{%s}}'%self.name)
            symbol = marker._A
            marker.orient_along(axis)
            marker_eq = sm.Eq(symbol,marker.A)

            mi_bar      = marker.express(self.body_i)
            mi_bar_eq   = sm.Eq(self.mi_bar.A, mi_bar)

            mj_bar      = marker.express(self.body_j)
            mj_bar_eq   = sm.Eq(self.mj_bar.A, mj_bar)

            assignments = [ui_bar_eq,uj_bar_eq,mi_bar_eq,mj_bar_eq]
            return assignments
    
    def numerical_arguments(self):
        from source.symbolic_classes.bodies import body
        from source.symbolic_classes.algebraic_constraints import algebraic_constraints as algebraic_constraints
        if isinstance(self,body):
            R = sm.Eq(self.R,sm.MutableDenseMatrix([0,0,0]))
            P = sm.Eq(self.P,sm.MutableDenseMatrix([1,0,0,0]))
            Rd = sm.Eq(self.Rd,sm.MutableDenseMatrix([0,0,0]))
            Pd = sm.Eq(self.Pd,sm.MutableDenseMatrix([1,0,0,0]))
            return [R,P,Rd,Pd]
        
        elif isinstance(self,algebraic_constraints):
            loc  = vector('pt_%s'%self.name)
            axis = vector('ax_%s'%self.name)
            
            loc  = sm.Eq(loc,sm.MutableDenseMatrix([0,0,0]))
            axis = sm.Eq(axis,sm.MutableDenseMatrix([0,0,1]))
            return [loc,axis]
