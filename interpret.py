#IPPcode22 language interpreter, 2. part of IPP project
#Author: Martin Zmitko (xzmitk01@stud.fit.vutbr.cz)

import sys
import re
import distutils.util
from turtle import st
import xml.etree.ElementTree as et
import argparse

frameGF = {}
frameTF = None
stackLF = []
stackCall = []
stackData = []

def error(code):
    if code == 31:
        print('Incorrect XML format', file=sys.stderr)
    elif code == 32:
        print('Incorrect XML structure', file=sys.stderr)
    elif code == 52:
        print('Semantics check error', file=sys.stderr)
    elif code == 53:
        print('Interpretation error: Wrong operand types', file=sys.stderr)
    elif code == 54:
        print('Interpretation error: Variable does not exist', file=sys.stderr)
    elif code == 55:
        print('Interpretation error: Frame does not exist', file=sys.stderr)
    elif code == 56:
        print('Interpretation error: Missing value', file=sys.stderr)
    elif code == 57:
        print('Interpretation error: Wrong operand value', file=sys.stderr)
    elif code == 58:
        print('Interpretation error: Incorrect string operation', file=sys.stderr)
    exit(code)

def parseArgs():
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('-s', '--source', type=str, help="Source code XML file (stdin if not set)")
    group.add_argument('-i', '--input', type=str, help="Interpretation input file (stdin if not set)")
    try:
        return parser.parse_args()
    except SystemExit as e: #exit with the correct return code on error
        if e.code != 0:
            exit(10)
        raise e

def parseFloat(string):
    if '0x' in string or 'p' in string:
        return float.fromhex(string)
    else:
        return float(string)

def parseXML(source):
    try:
        root = et.fromstring(source.read())
    except Exception:
        error(31)

    try:
        if root.tag != 'program' or root.attrib['language'] != "IPPcode22":
            error(32)

        instructions = {}
        labels = {}
        for instruction in root:
            if instruction.tag != 'instruction':
                error(32)
            args = {}
            for arg in instruction:
                if re.match(r'arg[1-3]', arg.tag) is None:
                    error(32)

                if arg.attrib['type'] == 'int':
                    value = int(arg.text)
                elif arg.attrib['type'] == 'float':
                    value = parseFloat(arg.text)
                elif arg.attrib['type'] == 'bool':
                    value = distutils.util.strtobool(arg.text)
                elif arg.attrib['type'] == 'label' and instruction.attrib['opcode'] == 'LABEL':
                    if arg.text in labels:
                        error(52)
                    labels[arg.text] = int(instruction.attrib['order'])
                    value = arg.text
                elif arg.attrib['type'] == 'nil':
                    if arg.text != 'nil':
                        error(32)
                    value = arg.text
                else:
                    value = arg.text
                    if value is None:
                        value = ''
                    value = re.sub(r'\\[0-9]{3}', lambda m: chr(int(m.group()[1:])), value)

                args[int(arg.tag[-1:]) - 1] = {'type': arg.attrib['type'], 'value': value}

            order = int(instruction.attrib['order'])
            if order in instructions or order < 1:
                error(32)
            instructions[order] = {'opcode': instruction.attrib['opcode'].upper(), 'args': args}
    except Exception:
        error(32)

    instrList = []
    for i, instr in enumerate(sorted(instructions.items())):
        instrList.append(instr[1])
        if instr[1]['opcode'] == 'LABEL':
            labels[instr[1]['args'][0]['value']] = i
    return instrList, labels

def peekLF(var=None):
    try:
        if type(var) is str:
            return stackLF[len(stackLF) - 1][var]
        else:
            return stackLF[len(stackLF) - 1]
    except IndexError:
        error(55)
    except KeyError:
        error(54)

def getArgValue(arg):
    if arg['type'] == 'var':
        try:
            var = arg['value'].split('@')
            if var[0] == 'GF':
                out = frameGF[var[1]]
            elif var[0] == 'LF':
                out = peekLF(var[1])
            elif var[0] == 'TF':
                out = frameTF[var[1]]
        except KeyError:
            error(54)
        except TypeError:
            error(55)
        if out is None:
            error(56)
        return out
    else:
        return {'type': arg['type'], 'value': arg['value']}

def setVarValue(var, arg):
    varSplit = var['value'].split('@')
    if varSplit[0] == 'GF':
        if varSplit[1] not in frameGF:
            error(54)
        frameGF[varSplit[1]] = arg
    elif varSplit[0] == 'LF':
        if varSplit[1] not in peekLF():
            error(54)
        peekLF()[varSplit[1]] = arg
    elif varSplit[0] == 'TF':
        if frameTF is None:
            error(55)
        if varSplit[1] not in frameTF:
            error(54)
        frameTF[varSplit[1]] = arg

def isStackOp(instr):
    return instr['opcode'][-1:] == 'S'

def getStackTop():
    if not stackData:
        error(56)
    return stackData.pop()

def operation(instr):
    symb2 = getStackTop() if isStackOp(instr) else getArgValue(instr['args'][2])
    symb1 = getStackTop() if isStackOp(instr) else getArgValue(instr['args'][1])
    if symb1['type'] != symb2['type'] or symb1['type'] not in ['int', 'float'] or (instr['opcode'] in ['IDIV', 'IDIVS'] and symb1['type'] != 'int') or (instr['opcode'] in ['DIV', 'DIVS'] and symb1['type'] != 'float'):
        error(53)
    try:
        value = symb1['value'] + symb2['value'] if instr['opcode'] in ['ADD', 'ADDS'] else\
                symb1['value'] - symb2['value'] if instr['opcode'] in ['SUB', 'SUBS'] else\
                symb1['value'] * symb2['value'] if instr['opcode'] in ['MUL', 'MULS'] else\
                symb1['value'] // symb2['value'] if instr['opcode'] in ['IDIV', 'IDIVS'] else\
                symb1['value'] / symb2['value']
    except Exception:
        error(57)
    
    if isStackOp(instr):
        stackData.append({'type': symb1['type'], 'value': value})
    else:
        setVarValue(instr['args'][0], {'type': symb1['type'], 'value': value})

def compare(instr):
    symb2 = getStackTop() if isStackOp(instr) else getArgValue(instr['args'][2])
    symb1 = getStackTop() if isStackOp(instr) else getArgValue(instr['args'][1])
    if symb1['type'] not in ['int', 'float', 'bool', 'string'] or symb1['type'] not in ['int', 'float', 'bool', 'string'] or symb1['type'] != symb2['type']:
        error(53)
    if instr['opcode'] in ['LT', 'LTS']:
        result = {'type': 'bool', 'value': symb1['value'] < symb2['value']}
    else:
        result = {'type': 'bool', 'value': symb1['value'] > symb2['value']}
    if isStackOp(instr):
        stackData.append(result)
    else:
        setVarValue(instr['args'][0], result)

def equal(instr):
    symb1 = getStackTop() if isStackOp(instr) else getArgValue(instr['args'][1])
    symb2 = getStackTop() if isStackOp(instr) else getArgValue(instr['args'][2])
    isNil = symb1['type'] == 'nil' or symb2['type'] == 'nil'
    if symb1['type'] not in ['int', 'float', 'bool', 'string', 'nil'] or symb1['type'] not in ['int', 'float', 'bool', 'string', 'nil'] or\
        (symb1['type'] != symb2['type'] and not isNil):
        error(53)
    if isNil:
        result = {'type': 'bool', 'value': symb1['type'] == symb2['type']}
    else:
        result = {'type': 'bool', 'value': symb1['value'] == symb2['value']}
    if isStackOp(instr):
        stackData.append(result)
    else:
        setVarValue(instr['args'][0], result)

def main():
    global frameTF, stackData
    args = parseArgs()
    try:
        source = open(args.source) if args.source else sys.stdin
        inp = open(args.input) if args.input else sys.stdin
    except OSError as e:
        print(e, file=sys.stderr)
        exit(11)

    instr, labels = parseXML(source)

    i = 0
    while i < len(instr):
        if instr[i]['opcode'] == 'MOVE':
            setVarValue(instr[i]['args'][0], getArgValue(instr[i]['args'][1]))
        elif instr[i]['opcode'] == 'CREATEFRAME':
            frameTF = {}
        elif instr[i]['opcode'] == 'PUSHFRAME':
            if frameTF is None:
                error(55)
            stackLF.append(frameTF)
            frameTF = None
        elif instr[i]['opcode'] == 'POPFRAME':
            try:
                frameTF = stackLF.pop()
            except IndexError:
                error(55)
        elif instr[i]['opcode'] == 'DEFVAR':
            var = instr[i]['args'][0]['value'].split('@')
            try:
                if var[0] == 'GF':
                    if var[1] in frameGF:
                        error(52)
                    frameGF[var[1]] = None
                elif var[0] == 'LF':
                    if var[1] in peekLF():
                        error(52)
                    peekLF()[var[1]] = None
                elif var[0] == 'TF':
                    if var[1] in frameTF:
                        error(52)
                    frameTF[var[1]] = None
            except Exception:
                error(55)
        elif instr[i]['opcode'] == 'CALL':
            stackCall.append(i + 1)
            if instr[i]['args'][0]['value'] not in labels:
                error(52)
            i = labels[instr[i]['args'][0]['value']]
            continue
        elif instr[i]['opcode'] == 'RETURN':
            try:
                i = stackCall.pop()
            except IndexError:
                error(56)
            continue
        elif instr[i]['opcode'] == 'PUSHS':
            stackData.append(getArgValue(instr[i]['args'][0]))
        elif instr[i]['opcode'] == 'POPS':
            setVarValue(instr[i]['args'][0], getStackTop())
        elif instr[i]['opcode'] == 'CLEARS':
            stackData = []
        elif instr[i]['opcode'] in ['ADD', 'SUB', 'MUL', 'DIV', 'IDIV', 'ADDS', 'SUBS', 'MULS', 'DIVS', 'IDIVS']:
            operation(instr[i])
        elif instr[i]['opcode'] in ['LT', 'GT', 'LTS', 'GTS']:
            compare(instr[i])
        elif instr[i]['opcode'] in ['EQ', 'EQS']:
            equal(instr[i])
        elif instr[i]['opcode'] in ['AND', 'OR', 'ANDS', 'ORS']:
            symb2 = getStackTop() if isStackOp(instr[i]) else getArgValue(instr[i]['args'][2])
            symb1 = getStackTop() if isStackOp(instr[i]) else getArgValue(instr[i]['args'][1])
            if symb1['type'] != 'bool' or symb2['type'] != 'bool':
                error(53)
            result = {'type': 'bool', 'value': symb1['value'] and symb2['value'] if instr[i]['opcode'] in ['AND', 'ANDS'] else symb1['value'] or symb2['value']}
            if isStackOp(instr[i]):
                stackData.append(result)
            else:
                setVarValue(instr[i]['args'][0], result)
        elif instr[i]['opcode'] in ['NOT', 'NOTS']:
            symb1 = getStackTop() if isStackOp(instr[i]) else getArgValue(instr[i]['args'][1])
            if symb1['type'] != 'bool':
                error(53)
            if isStackOp(instr[i]):
                stackData.append({'type': 'bool', 'value': not symb1['value']})
            else:
                setVarValue(instr[i]['args'][0], {'type': 'bool', 'value': not symb1['value']})
        elif instr[i]['opcode'] in ['FLOAT2INT', 'FLOAT2INTS', 'INT2FLOAT', 'INT2FLOATS']:
            symb1 = getStackTop() if isStackOp(instr[i]) else getArgValue(instr[i]['args'][1])
            type = 'float' if instr[i]['opcode'] in ['FLOAT2INT', 'FLOAT2INTS'] else 'int'
            if symb1['type'] != type:
                error(53)
            if isStackOp(instr[i]):
                stackData.append({'type': 'int' if type == 'float' else 'float', 'value': int(symb1['value']) if type == 'float' else float(symb1['value'])})
            else:
                setVarValue(instr[i]['args'][0], {'type': 'int' if type == 'float' else 'float', 'value': int(symb1['value']) if type == 'float' else float(symb1['value'])})
        elif instr[i]['opcode'] in ['INT2CHAR', 'INT2CHARS']:
            symb1 = getStackTop() if isStackOp(instr[i]) else getArgValue(instr[i]['args'][1])
            if symb1['type'] != 'int':
                error(53)
            try:
                if isStackOp(instr[i]):
                    stackData.append({'type': 'string', 'value': chr(symb1['value'])})
                else:
                    setVarValue(instr[i]['args'][0], {'type': 'string', 'value': chr(symb1['value'])})
            except ValueError:
                error(58)
        elif instr[i]['opcode'] in ['STRI2INT', 'STRI2INTS']:
            symb2 = getStackTop() if isStackOp(instr[i]) else getArgValue(instr[i]['args'][2])
            symb1 = getStackTop() if isStackOp(instr[i]) else getArgValue(instr[i]['args'][1])
            if symb1['type'] != 'string' or symb2['type'] != 'int':
                error(53)
            try:
                if symb2['value'] < 0:
                    raise IndexError
                if isStackOp(instr[i]):
                    stackData.append({'type': 'int', 'value': ord(symb1['value'][symb2['value']])})
                else:
                    setVarValue(instr[i]['args'][0], {'type': 'int', 'value': ord(symb1['value'][symb2['value']])})
            except IndexError:
                error(58)
        elif instr[i]['opcode'] == 'READ':
            symb1 = getArgValue(instr[i]['args'][1])
            if symb1['type'] != 'type' or symb1['value'] not in ['int', 'float', 'string', 'bool']:
                error(53)
            read = inp.readline().rstrip('\n')
            try:
                if symb1['value'] == 'int':
                    setVarValue(instr[i]['args'][0], {'type': 'int', 'value': int(read)})
                elif symb1['value'] == 'float':
                    setVarValue(instr[i]['args'][0], {'type': 'float', 'value': parseFloat(read)})
                elif symb1['value'] == 'string':
                    setVarValue(instr[i]['args'][0], {'type': 'string', 'value': read})
                elif symb1['value'] == 'bool':
                    setVarValue(instr[i]['args'][0], {'type': 'bool', 'value': read.lower() == 'true'})
            except Exception:
                setVarValue(instr[i]['args'][0], {'type': 'nil', 'value': 'nil'})
        elif instr[i]['opcode'] == 'WRITE':
            symb1 = getArgValue(instr[i]['args'][0])
            if symb1['type'] == 'nil':
                out = ''
            elif symb1['type'] == 'bool':
                out = 'true' if symb1['value'] else 'false'
            elif symb1['type'] == 'float':
                out = symb1['value'].hex()
            else:
                out = symb1['value']
            print(out, end='')
        elif instr[i]['opcode'] == 'CONCAT':
            symb1 = getArgValue(instr[i]['args'][1])
            symb2 = getArgValue(instr[i]['args'][2])
            if symb1['type'] != 'string' or symb2['type'] != 'string':
                error(53)
            setVarValue(instr[i]['args'][0], {'type': 'string', 'value': symb1['value'] + symb2['value']})
        elif instr[i]['opcode'] == 'STRLEN':
            symb1 = getArgValue(instr[i]['args'][1])
            if symb1['type'] != 'string':
                error(53)
            setVarValue(instr[i]['args'][0], {'type': 'int', 'value': len(symb1['value'])})
        elif instr[i]['opcode'] == 'GETCHAR':
            symb1 = getArgValue(instr[i]['args'][1])
            symb2 = getArgValue(instr[i]['args'][2])
            if symb1['type'] != 'string' or symb2['type'] != 'int':
                error(53)
            try:
                if symb2['value'] < 0:
                    raise IndexError
                setVarValue(instr[i]['args'][0], {'type': 'string', 'value': symb1['value'][symb2['value']]})
            except IndexError:
                error(58)
        elif instr[i]['opcode'] == 'SETCHAR':
            symb0 = getArgValue(instr[i]['args'][0])
            symb1 = getArgValue(instr[i]['args'][1])
            symb2 = getArgValue(instr[i]['args'][2])
            if symb0['type'] != 'string' or symb1['type'] != 'int' or symb2['type'] != 'string':
                error(53)
            try:
                if symb1['value'] < 0 or symb1['value'] >= len(symb0['value']):
                    raise IndexError
                out = symb0['value'][:symb1['value']] + symb2['value'][0] + symb0['value'][symb1['value'] + 1:]
                setVarValue(instr[i]['args'][0], {'type': 'string', 'value': out})
            except Exception:
                error(58)
        elif instr[i]['opcode'] == 'TYPE':
            if instr[i]['args'][1]['type'] == 'var':
                var = instr[i]['args'][1]['value'].split('@')
                try:
                    if var[0] == 'GF':
                        if var[1] not in frameGF:
                            error(54)
                        out = frameGF[var[1]]['type']
                    elif var[0] == 'LF':
                        if var[1] not in peekLF():
                            error(54)
                        out = peekLF()[var[1]]['type']
                    elif var[0] == 'TF':
                        if frameTF is None:
                            error(55)
                        if var[1] not in frameTF:
                            error(54)
                        out = frameTF[var[1]]['type']
                except Exception:
                    out = ''
                setVarValue(instr[i]['args'][0], {'type': 'string', 'value': out})
            else:
                setVarValue(instr[i]['args'][0], {'type': 'string', 'value': instr[i]['args'][1]['type']})
        elif instr[i]['opcode'] == 'LABEL':
            pass
        elif instr[i]['opcode'] == 'JUMP':
            symb0 = getArgValue(instr[i]['args'][0])
            try:
                i = labels[symb0['value']]
            except KeyError:
                error(52)
            continue
        elif instr[i]['opcode'] in ['JUMPIFEQ', 'JUMPIFNEQ', 'JUMPIFEQS', 'JUMPIFNEQS']:
            symb0 = getArgValue(instr[i]['args'][0])
            symb1 = getStackTop() if isStackOp(instr[i]) else getArgValue(instr[i]['args'][1])
            symb2 = getStackTop() if isStackOp(instr[i]) else getArgValue(instr[i]['args'][2])
            if symb0['value'] not in labels:
                error(52)
            isNil = symb1['type'] == 'nil' or symb2['type'] == 'nil'
            if symb0['type'] != 'label' or (symb1['type'] != symb2['type'] and not isNil):
                error(53)
            if isNil:
                out = symb1['type'] == symb2['type']
            else:
                out = symb1['value'] == symb2['value']
            if instr[i]['opcode'] in ['JUMPIFNEQ', 'JUMPIFNEQS']:
                out = not out
            if out:
                i = labels[symb0['value']]
                continue
        elif instr[i]['opcode'] == 'EXIT':
            symb0 = getArgValue(instr[i]['args'][0])
            if symb0['type'] != 'int':
                error(53)
            if symb0['value'] < 0 or symb0['value'] > 49:
                error(57)
            exit(symb0['value'])
        elif instr[i]['opcode'] == 'DPRINT':
            symb0 = getArgValue(instr[i]['args'][0])
            print(symb0['value'], file=sys.stderr)
        elif instr[i]['opcode'] == 'BREAK':
            print(f'Instruction number: {i}', file=sys.stderr)
            print(f'GF: {frameGF}', file=sys.stderr)
            print(f'LF: {stackLF}', file=sys.stderr)
            print(f'TF: {frameTF}', file=sys.stderr)
        else:
            error(32)
        i += 1

    source.close()
    inp.close()

if __name__ == "__main__":
    main()
