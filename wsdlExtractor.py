
inputfilenames = [] # leave this empty to process all .wsdl and .xsd files in the directory of the script
outputfilename = 'api.yaml'
#-------------------------------------------------
true = True
false = False

XS_SIMPLE_TYPE_START = '<xs:simpleType name='
XS_SIMPLE_TYPE_END = '</xs:simpleType>'
XSD_SIMPLE_TYPE_START = '<xsd:simpleType name='
XSD_SIMPLE_TYPE_END = '</xsd:simpleType>'
XSD_RESTRICTION_BASE = '<xsd:restriction base'
XSD_RESTRICTION_END = '</xsd:restriction>'
XS_RESTRICTION_BASE = '<xs:restriction base'
XS_RESTRICTION_END = '</xs:restriction>'

COMPLEX_TYPE_START = '<xs:complexType name='
COMPLEX_CONTENT_START = '<xs:sequence>'
COMPLEX_CONTENT_END = '</xs:sequence>'
COMPLEX_TYPE_END = '</xs:complexType>'
COMMENT = '<!--'
EXTENSION = '<xs:extension base="'
MAX_OCCURS_UNBOUNDED = 'maxOccurs="unbounded"'

extendedClassName___ = 'extendedClassName___'

scannedformats = ['wsdl', 'xsd']

simpleTypes = {}
types = {}
type_ = None
insideContent = false

def getfilesforscanning():
    global inputfilenames
    global scannedformats

    if len(inputfilenames) > 0:
        return inputfilenames
    
    import os
    return list(filter(lambda f: f[f.rindex('.')+1::] in scannedformats, [f for f in os.listdir('.') if os.path.isfile(f)]))

def joinLines(lines):
    output = ''
    for line in lines:
        output = output + line + '\n'
    return output

def extractType(line):
    if not ('name' in line):
        return None
    
    nameIndex = line.index('name=')
    typeIndex = 0
    
    if 'type=' in line:
        typeIndex = line.index('type=')
    elif 'base=' in line:
        typeIndex = line.index('base=')
    else:
        return None
    
    datatype = line[typeIndex::].split('"')[1]
    if ':' in datatype:
        datatype = datatype.split(':')[1]

    return {
        'dataname': line[nameIndex::].split('"')[1],
        'datatype': datatype,
        'array': MAX_OCCURS_UNBOUNDED in line
    }

def transform(datatype):
    if ':' in datatype:
        datatype=datatype[datatype.index(":")+1::]
    
    typemap = {
        'string': 'string',
        'long': 'integer',
        'int': 'integer',
        'boolean': 'boolean',
        'dateTime': 'date-time',
        'decimal': 'number'
    }
    if datatype in typemap:
        return typemap[datatype]
    
    return '#/definitions/' + datatype

def indent(line, level):
    return (2 * level * ' ') + line

def processOneComplexType(typename, types):
    value = types[typename]

    lines = []
    lines.append( indent(typename+':', 1) )
    
    if extendedClassName___ in value:
        lines.append( indent('allOf:', 2) )
        lines.append( indent('- $ref: \'#/definitions/'+value[extendedClassName___]+'\'', 3) )
    
    if len(list(filter(lambda k: k != extendedClassName___, value.keys()))) > 0:
        lines.append( indent('type: object', 2) )
        lines.append( indent('properties:', 2) )

    for fieldname in value.keys():
        if fieldname == extendedClassName___:
            continue
                
        datatype = value[fieldname]['datatype']
        isarray = value[fieldname]['array']
        
        lines.append( indent(fieldname + ':', 3) )
        
        if not isarray:
            if datatype == 'date-time':
                lines.append( indent('type: string', 4) )
                lines.append( indent('format: '+datatype, 4) )
            else:
                if '#' == datatype[0]:
                    lines.append( indent('$ref: \''+datatype+'\'', 4) )
                else:
                    lines.append( indent('type: '+datatype, 4) )
                    if 'format' in value[fieldname]:
                        lines.append( indent('format: '+value[fieldname]['format'], 4) )
        else:
            lines.append( indent('type: array', 4) )
            lines.append( indent('items: ', 4) )
            lines.append( indent('$ref: \''+datatype+'\'', 5) )
    
    return joinLines(lines)

def processOneSimpleType(typename, simpleTypes):
    value = simpleTypes[typename]
    lines = []
    lines.append( indent(typename+':', 1) )
    if 'enum' in value:
        lines.append( indent('type: string', 2) )
        lines.append( indent('enum: ' + str(value['enum']).replace('\'', ''), 2) )
        return joinLines(lines)
    elif 'type' in value and value['type'] == 'string':
        for key in value.keys():
            if type(value[key]) is str:
                lines.append( indent(key + ': ' + value[key], 2) )
            else:
                lines.append( indent(key+': '+str(value[key]).replace('\'', ''),2) )
        return joinLines(lines)
    else:
        lines.append( indent('type: object', 2) )

    lines.append( indent('properties: ',2) )
    lines.append( indent('value: ',3) )

    for key in value.keys():
        if type(value[key]) is str:
            lines.append( indent(key + ': ' + value[key], 4) )
        else:
            lines.append( indent(key+': '+str(value[key]).replace('\'', ''),4) )
    
    return joinLines(lines)

def extractSimpleTypes(filename):
    global insideContent

    with open(filename, encoding="utf-8") as file:
        insideRestriction = false
        for line in file:
            line = line.replace(' =', '=')
            line = line.replace('= ', '=')
            if COMMENT in line:
                continue
            if XS_SIMPLE_TYPE_START in line or XSD_SIMPLE_TYPE_START in line:
                type_ = line.split('"')[1]
                simpleTypes[type_] = {}
                insideContent = true
            if XS_SIMPLE_TYPE_END in line or XSD_SIMPLE_TYPE_END in line:
                insideContent = false
                insideRestriction = false
            if not insideContent:
                continue
            if XSD_RESTRICTION_BASE in line or XS_RESTRICTION_BASE in line:
                name = line.split('"')[1]
                if ':' in name:
                    name = name.split(':')[1]

                transformed = transform( name )
                simpleTypes[type_]['type'] = transformed
                if name == 'long':
                    simpleTypes[type_]['format'] = 'int64'
                elif name == 'decimal':
                    simpleTypes[type_]['format'] = 'double'
                insideRestriction = true
                continue
            if XSD_RESTRICTION_END in line or XS_RESTRICTION_END in line:
                insideRestriction = false
            if insideRestriction:
                paramname = line.split(':')[1].split(' ')[0]
                paramvalue = line.split('"')[1]
                if paramname == 'enumeration':
                    if 'enum' in simpleTypes[type_]:
                        simpleTypes[type_]['enum'].append(paramvalue)
                    else:
                        simpleTypes[type_]['enum'] = [paramvalue]
                elif paramname == 'length':
                    simpleTypes[type_]['minLength'] = paramvalue
                    simpleTypes[type_]['maxLength'] = paramvalue
                elif paramname == 'pattern':
                    simpleTypes[type_][paramname] = '\''+paramvalue+'\''
                elif paramname in ['whiteSpace', 'totalDigits', 'fractionDigits']:
                    pass
                else:
                    simpleTypes[type_][paramname] = paramvalue

def extractComplexTypes(filename):
    global insideContent

    with open("TechUserMgm_v1.wsdl", encoding="utf-8") as file:
    
        for line in file:
            if COMMENT in line:
                continue
            if COMPLEX_TYPE_START in line:
                type_ = line.split('"')[1]
                types[type_] = {}
                insideContent = true
            elif COMPLEX_CONTENT_START in line:
                insideContent = true
            elif COMPLEX_TYPE_END in line:
                insideContent = false
            elif EXTENSION in line:
                types[type_][extendedClassName___] = line.split('"')[1].split(":")[1]

            if insideContent:
                typedef = extractType(line)
                if typedef is not None:
                    
                    types[type_][typedef['dataname']] = {'datatype': transform(typedef['datatype']), 'array': typedef['array']}    
                    if typedef['datatype'] == 'long':
                        types[type_][typedef['dataname']]['format'] = 'int64'
                    elif typedef['datatype'] == 'decimal':
                        types[type_][typedef['dataname']]['format'] = 'double'
#-----------------------------------------------------#
# End of function definitions and start of processing #
#-----------------------------------------------------#

inputfilenames = getfilesforscanning()
for file in inputfilenames:
    extractSimpleTypes(file)
    extractComplexTypes(file)

result = 'definitions:\n'
for entry in simpleTypes.keys():
    result = result + processOneSimpleType(entry, simpleTypes)

for entry in types.keys():
    result = result + processOneComplexType(entry, types)

outfile = open(outputfilename, 'w', encoding="utf-8")
outfile.write(result)
outfile.close()
print('We\'re done! :) ')
