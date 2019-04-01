# -*- coding: utf-8 -*-
"""
Created on Wed Mar 27 08:49:16 2019

@author: khaled.ghobashy
"""
import os
import pickle
import cloudpickle

import source.mbs_creators.topology_classes as topology_classes
from source.mbs_creators.configuration_classes import abstract_configuration
import source.symbolic_classes.joints as joints
import source.symbolic_classes.forces as forces

from source.code_generators.python_code_generators import template_code_generator


class topology(object):
    
    def __init__(self, script_path):
        
        self.script_path = script_path
        
        self.name = os.path.basename(script_path).split('.')[0]
        self._mbs = topology_classes.template_based_topology(self.name)
        
        self._decorate_joints()
        self._decorate_actuators()
        self._decorate_forces()
        
    def add_body(self, *args, **kwargs):
        self._mbs.add_body(*args, **kwargs)
    
    @property
    def add_joint(self):
        return self._joints
    
    @property
    def add_actuator(self):
        return self._actuators
    
    @property
    def add_force(self):
        return self._forces
    
    def assemble_model(self):
        self._mbs.assemble_model()
        
    def write_python_code(self):
        numerical_code = template_code_generator(self._mbs)
        numerical_code.write_code_file()
        
    def save(self):
        file = '%s.stpl'%os.path.splitext(self.script_path)[0]
        with open(file,'wb') as f:
            cloudpickle.dump(self, f)
    
    @staticmethod
    def reload(script_path):
        file = '%s.stpl'%os.path.splitext(script_path)[0]
        with open(file, 'rb') as f:
            template = pickle.load(f)
        return template
    
    
    def _decorate_joints(self):
        container_name  = 'joints_container'
        container_items = ['spherical', 'revolute', 'universal', 'translational',
                           'cylinderical', 'tripod', 'fixed']
        container = self._decorate_edge_components(container_name, container_items, joints)
        self._joints = container
    
    def _decorate_actuators(self):  
        container_name  = 'actuators_container'
        container_items = ['rotational_actuator', 'absolute_locator']
        container = self._decorate_edge_components(container_name, container_items, joints)
        self._actuators = container
    
    def _decorate_forces(self):    
        container_name  = 'forces_container'
        container_items = ['internal_force']
        container = self._decorate_edge_components(container_name, container_items, forces)
        self._forces = container

        
    def _decorate_edge_components(self, container_name, container_items, module):   
        container_class = type(container_name, (object,), {})
        def dummy_init(dself): pass
        container_class.__init__ = dummy_init
        container_instance = container_class()
        for name in container_items:
            component = getattr(module, name)
            decorated_component = self._decorate_as_edge(component)
            setattr(container_instance, name, decorated_component)
        return container_instance
    
    def _decorate_as_edge(self, typ):
        if issubclass(typ, joints.absolute_locator):
            def decorated(*args, **kwargs):
                self._mbs.add_absolute_actuator(typ, *args, **kwargs)
        
        elif issubclass(typ, joints.rotational_actuator):
            def decorated(*args, **kwargs):
                self._mbs.add_joint_actuator(typ, *args, **kwargs)
        
        elif issubclass(typ, forces.generic_force):
            def decorated(*args, **kwargs):
                self._mbs.add_force(typ, *args, **kwargs)
        
        else:
            def decorated(*args, **kwargs):
                self._mbs.add_joint(typ, *args, **kwargs)
        return decorated


###############################################################################
###############################################################################

class assembly(object):
    
    def __init__(self, name):
        self._mbs = topology_classes.assembly(name)
        
    def add_subsystem(self, subsystem):
        self._mbs.add_subsystem(subsystem)
        
    def assign_virtual_body(self, virtual_node, actual_node):
        self._mbs.assign_virtual_body(virtual_node, actual_node)
            
###############################################################################
###############################################################################

class configuration(object):
    
    def __init__(self, name, model_instance):
        self.name = name
        self._config = abstract_configuration(name, model_instance)
        self._decorate_methods()
    
    @property
    def add_point(self):
        return self._point_methods
    
    @property
    def add_vector(self):
        return self._vector_methods
    
    @property
    def add_scalar(self):
        return self._scalar_methods
    
    @property
    def add_geometry(self):
        return self._geometry_methods
    
    @property
    def add_relation(self):
        return self._relation_methods
    
    def _decorate_methods(self):
        self._decorate_point_methods()
        self._decorate_vector_methods()
        self._decorate_scalar_methods()
        self._decorate_geometry_methods()
        self._decorate_relation_methods()

    def _decorate_point_methods(self):
        sym = 'hp'
        node_type = vector
        methods = ['Mirrored', 'Centered', 'Equal_to', 'UserInput']
        self._point_methods = self._decorate_components(node_type, sym, methods, CR)
        
    def _decorate_vector_methods(self):
        sym = 'vc'
        node_type = vector
        methods = ['Mirrored', 'Oriented', 'Equal_to', 'UserInput']
        self._vector_methods = self._decorate_components(node_type, sym, methods, CR)

    def _decorate_scalar_methods(self):
        sym = ''
        node_type = sm.symbols
        methods = ['Equal_to', 'UserInput']
        self._scalar_methods = self._decorate_components(node_type, sym, methods, CR)
            
    def _decorate_geometry_methods(self):
        sym = 'gm'
        node_type = Geometry
        methods = ['Composite_Geometry', 'Cylinder_Geometry', 'Triangular_Prism']
        self._geometry_methods = self._decorate_components(node_type, sym, methods, Geometries)

    def _decorate_components(self, node_type, sym, methods_list, methods_class):   
        container_class = type('container', (object,), {})
        def dummy_init(dself): pass
        container_class.__init__ = dummy_init
        container_instance = container_class()

        for name in methods_list:
            method = getattr(methods_class, name)
            decorated_method = self._decorate_as_attr(node_type, sym, method)
            setattr(container_instance, name, decorated_method)
        
        return container_instance
    
    def _decorate_as_attr(self, node_type, sym, construction_method):
        
        if construction_method is None:
            def decorated(*args, **kwargs):
                self._add_node(node_type, args[0], **kwargs, sym=sym)
            decorated.__doc__ = ''
        
        elif node_type is None:
            def decorated(*args, **kwargs):
                self._add_relation(construction_method, *args, **kwargs)
            decorated.__doc__ = construction_method.__doc__
       
        else:
            def decorated(*args, **kwargs):
                node = self._add_node(node_type, args[0], **kwargs, sym=sym)
                self._add_relation(construction_method, node, *args[1:], **kwargs)
            decorated.__doc__ = construction_method.__doc__
        
        return decorated


