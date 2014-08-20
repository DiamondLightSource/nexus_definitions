#!/usr/bin/env python

'''
Read the the NeXus NXDL class specification and describe it.  
Write a restructured text (.rst) document for use in the NeXus manual in 
the NeXus NXDL Classes chapter.
'''

# testing:
# cd /tmp
# mkdir out
# /G/nx-def/utils/nxdl2rst.py /G/nx-def/applications/NXsas.nxdl.xml > nxsas.rst && sphinx-build . out
# then point browser to file:///tmp/out/nxsas.html

from __future__ import print_function
import os, sys, re
from collections import OrderedDict
import lxml.etree
try:
    from pyRestTable import rest_table
except:
    import rst_table as rest_table 

# find the directory of this python file
BASEDIR = os.path.split(os.path.abspath(__file__))[0]

def printf(str, *args):
    print(str % args, end='')

def fmtTyp( node ):
    typ = node.get('type', 'untyped (:ref:`NX_CHAR <NX_CHAR>`)')
    if typ.startswith('NX_'):
        typ = ':ref:`%s <%s>`' % (typ, typ)
    return typ

def fmtUnits( node ):
    units = node.get('units', '')
    if not units:
        return ''
    if units.startswith('NX_'):
        units = '\ :ref:`%s <%s>`' % (units, units)
    return ' {units=%s}' % units

def getDocBlocks( ns, node ):
    docnodes = node.xpath('nx:doc', namespaces=ns)
    if docnodes is None or len(docnodes)==0:
        return ''
    if len(docnodes) > 1:
        things = (node.sourceline, os.path.split(node.base)[1])
        raise Exception( 'Too many doc elements: line %d, %s' % things )
    
    # be sure to grab _all_ content in the documentation
    # it might look like XML
    s = lxml.etree.tostring(docnodes[0], pretty_print=True)
    p1 = s.find('>')+1
    p2 = s.rfind('</')
    text = s[p1:p2]
    # Remove indentation; remove single \n; \n\n become \n
    blocks = re.split( '\n\s*\n', text )
    blocks = [ re.sub( '\s*\n\s*', ' ', block ).lstrip().rstrip() for block in blocks ]
    return blocks

def getDocLine( ns, node ):
    blocks = getDocBlocks( ns, node )
    if len(blocks)==0:
        return ''
    if len(blocks)>1:
        raise Exception( 'Unexpected multi-paragraph doc at ' %
                         node.get('name') )
    return blocks[0]

def analyzeDimensions( ns, parent ):
    node_list = parent.xpath('nx:dimensions', namespaces=ns)
    if len(node_list) != 1:
        return ''
    node = node_list[0]
    # rank = node.get('rank') # ignore this
    node_list = node.xpath('nx:dim', namespaces=ns)
    dims = []
    for subnode in node_list:
        value = subnode.get('value')
        if not value:
            value = 'ref(%s)' % subnode.get('ref')
        dims.append( value )
    return '[%s]' % ( ', '.join(dims) )

def printEnumeration( indent, ns, parent ):
    node_list = parent.xpath('nx:item', namespaces=ns)
    if len(node_list) == 0:
        return ''

    if len(node_list) == 1:
        printf( '%sObligatory value:' % ( indent ) )
    else:
        printf( '%sAny of these values:' % ( indent ) )

    docs = OrderedDict()
    for item in node_list:
        name = item.get('value')
        docs[name] = getDocLine(ns, item)

    if any( doc for doc in docs.values() ):
        print('')
        for name, doc in docs.items():
            printf( '%s  %s' % ( indent, name ) )
            if doc:
                printf( ': %s' % ( doc ) )
            print('\n')
    else:
        print(' %s' % ( ' | '.join( docs.keys() ) ) )
    print('')

def printDoc( indent, ns, node, required=False):
    blocks = getDocBlocks(ns, node)
    if len(blocks)==0:
        if required:
            raise Exception( 'No documentation for: ' + node.get('name') )
        print('')
    else:
        for block in blocks:
            print( '%s%s\n' % ( indent, block ) )

def printAttribute( ns, node, indent ):
    print( '%s**%s**: %s%s' % (
        indent, '@'+node.get('name'), fmtTyp(node), fmtUnits(node) ) )
    printDoc(indent+'  ', ns, node)


def printFullTree(ns, parent, name, indent):
    '''
    recursively print the full tree structure
    
    :param dict ns: dictionary of namespaces for use in XPath expressions
    :param lxml_element_node parent: parent node to be documented
    :param str name: name of elements, such as NXentry/NXuser
    :param indent: to keep track of indentation level
    '''

    for node in parent.xpath('nx:field', namespaces=ns):
        name = node.get('name')
        dims = analyzeDimensions(ns, node)
        print( '%s**%s%s**: %s%s\n' % (
            indent, name, dims, fmtTyp(node), fmtUnits(node) ) )

        printDoc(indent+'  ', ns, node)

        node_list = node.xpath('nx:enumeration', namespaces=ns)
        if len(node_list) == 1:
            printEnumeration( indent+'  ', ns, node_list[0] )

        # TODO: look for "deprecated" element, add to doc

        for subnode in node.xpath('nx:attribute', namespaces=ns):
            printAttribute( ns, subnode, indent+'  ' )
    
    for node in parent.xpath('nx:group', namespaces=ns):
        name = node.get('name', '')
        typ = node.get('type', 'untyped (this is an error; please report)')
        if typ.startswith('NX'):
            if name is '':
                name = '(%s)' % typ.lstrip('NX')
            typ = ':ref:`%s`' % typ
        print( '%s**%s**: %s\n' % (indent, name, typ ) )

        printDoc(indent+'  ', ns, node)

        for subnode in node.xpath('nx:attribute', namespaces=ns):
            printAttribute( ns, subnode, indent+'  ' )

        nodename = '%s/%s' % (name, node.get('type'))
        printFullTree(ns, node, nodename, indent+'  ')

    for node in parent.xpath('nx:link', namespaces=ns):
        print( '%s**%s** --> %s\n' % (
            indent, node.get('name'), node.get('target') ) )
        printDoc(indent+'  ', ns, node)


if __name__ == '__main__':

    # get NXDL_SCHEMA_FILE
    developermode = True
    developermode = False
    if developermode and len(sys.argv) != 2:
        # use default input file
        NXDL_SCHEMA_FILE = os.path.join(BASEDIR, '..', 'applications', 'NXarchive.nxdl.xml')
        NXDL_SCHEMA_FILE = os.path.join(BASEDIR, '..', 'applications', 'NXsas.nxdl.xml')
        #NXDL_SCHEMA_FILE = os.path.join(BASEDIR, '..', 'base_classes', 'NXcrystal.nxdl.xml')
        #NXDL_SCHEMA_FILE = os.path.join(BASEDIR, '..', 'base_classes', 'NXobject.nxdl.xml')
        #NXDL_SCHEMA_FILE = os.path.join(BASEDIR, '..', 'contributed_definitions', 'NXarpes.nxdl.xml')
        #NXDL_SCHEMA_FILE = os.path.join(BASEDIR, '..', 'contributed_definitions', 'NXmagnetic_kicker.nxdl.xml')
        
    else:
        # get input file from command line
        if len(sys.argv) != 2:
            print( 'usage: %s someclass.nxdl.xml' % sys.argv[0] )
            exit()
        NXDL_SCHEMA_FILE = sys.argv[1]

    # parse input file into tree
    if not os.path.exists(NXDL_SCHEMA_FILE):
        print( 'Cannot find %s' % NXDL_SCHEMA_FILE )
        exit()
    tree = lxml.etree.parse(NXDL_SCHEMA_FILE)

    # The following URL is outdated, but that doesn't matter;
    # it won't be accessed; it's just an arbitrary namespace name.
    # It only needs to match the xmlns attribute in the NXDL files.
    NAMESPACE = 'http://definition.nexusformat.org/nxdl/@NXDL_RELEASE@'
    ns = {'nx': NAMESPACE}
    
    root = tree.getroot()
    name = root.get('name')
    title = name

    subdir = os.path.split(os.path.split(tree.docinfo.URL)[0])[1]
    index_cat = {
                 'base_classes': 'Base Classes',
                 'applications': 'Application Definitions',
                 'contributed_definitions': 'Contributed Definitions',
                 }[subdir]

    # print ReST comments and section header
    print( '.. auto-generated by script %s from the NXDL source %s' %
           (sys.argv[0], sys.argv[1]) )
    print('')
    print( '.. index:: ! class definition -- %s; %s' % (index_cat, name) )
    print( '.. index:: ! %s' % name )
    print('')
    print( '.. _%s:\n' % name )
    print( '='*len(title) )
    print( title )
    print( '='*len(title) )

    # print category
    print('')
    print( '**Category**:' )
    print( '  %s.' % ( root.get('category').strip() ) )

    # print official description of this class
    print('')
    print( '**Description**:' )
    printDoc('  ', ns, root, required=True)

    # print category
    extends = root.get('extends')
    if extends is not None:
        extends = ':ref:`%s`' % extends
    else:
        extends = ''
    print('')
    print( '**Extends**:' )
    print( '  %s.\n' % ( extends ) )

    # TODO: change instances of \t to proper indentation
    html_root = 'https://github.com/nexusformat/definitions/blob/master'
        
    # print experimental full tree
    print( '**Structure**:\n' )
    printFullTree(ns, root, name, '  ')

    # print symbol list
    node_list = root.xpath('nx:symbols', namespaces=ns)
    print( '**Symbols**:\n' )
    if len(node_list) == 0:
        print( '  No symbol table.\n' )
    elif len(node_list) > 1:
        raise Exception( 'Invalid symbol table in ' % root.get('name') )
    else:
        printDoc( '  ', ns, node_list[0] )
        for node in node_list[0].xpath('nx:symbol', namespaces=ns):
            doc = getDocLine(ns, node)
            printf( '  %s' % node.get('name') )
            if doc:
                printf( ': %s' % doc )
            print('\n')

    # print group references
    print( '**Groups cited**:' )
    node_list = root.xpath('//nx:group', namespaces=ns)
    groups = []
    for node in node_list:
        g = node.get('type')
        g_ref = ':ref:`%s`' % g
        if g.startswith('NX') and g_ref not in groups:
            groups.append(g_ref)
    txt = 'none'
    if len(groups) > 0:
        txt = ', '.join(sorted(groups))
    print( '  %s.\n' % ( txt ) )

    # print history (currently, only a version number is available)
    print( '**History**:' )
    print( '  Introduced in NeXus version %s.\n' %
           ( root.get('version').strip() ) )

    # print NXDL source location
    print( '**Source**:' )
    print( '  Automatically generated from %s/%s/%s.nxdl.xml.' % (
        html_root, subdir, name) )
