"""Small helpers for writing flow XML."""
import sys
from xml.sax.saxutils import escape as e

def val(v):
    if v is None:
        return ''
    kind, x = v
    if kind == 'ref':
        return f'<elementReference>{x}</elementReference>'
    if kind == 'str':
        return f'<stringValue>{e(x)}</stringValue>'
    if kind == 'num':
        return f'<numberValue>{x}</numberValue>'
    if kind == 'bool':
        return f'<booleanValue>{x}</booleanValue>'
    raise ValueError(kind)

REF = lambda x: ('ref', x)
STR = lambda x: ('str', x)
NUM = lambda x: ('num', x)
BOOL = lambda x: ('bool', 'true' if x else 'false')

def conn(t, tag='connector'):
    return f'<{tag}><targetReference>{t}</targetReference></{tag}>' if t else ''

def loc():
    return '<locationX>0</locationX><locationY>0</locationY>'

els = {k: [] for k in ['assignments', 'choices', 'decisions', 'dynamicChoiceSets', 'formulas', 'loops',
                       'recordCreates', 'recordLookups', 'screens', 'variables']}

def assignment(name, label, items, nxt):
    x = f'<assignments><name>{name}</name><label>{e(label)}</label>{loc()}'
    for ref, op, v in items:
        x += f'<assignmentItems><assignToReference>{ref}</assignToReference><operator>{op}</operator><value>{val(v)}</value></assignmentItems>'
    els['assignments'].append(x + conn(nxt) + '</assignments>')

def cond(left, op, v):
    return f'<conditions><leftValueReference>{left}</leftValueReference><operator>{op}</operator><rightValue>{val(v)}</rightValue></conditions>'

def decision(name, label, rules, default, default_label='No'):
    x = f'<decisions><name>{name}</name><label>{e(label)}</label>{loc()}{conn(default, "defaultConnector")}<defaultConnectorLabel>{default_label}</defaultConnectorLabel>'
    for rname, rlabel, conds, nxt, logic in rules:
        x += f'<rules><name>{rname}</name><conditionLogic>{logic}</conditionLogic>{"".join(conds)}{conn(nxt)}<label>{e(rlabel)}</label></rules>'
    els['decisions'].append(x + '</decisions>')

def formula(name, dtype, expr, desc, scale=None):
    s = f'<scale>{scale}</scale>' if scale is not None else ''
    els['formulas'].append(f'<formulas><name>{name}</name><description>{e(desc)}</description><dataType>{dtype}</dataType><expression>{e(expr)}</expression>{s}</formulas>')

def loop(name, label, coll, nxt, done):
    els['loops'].append(f'<loops><name>{name}</name><label>{e(label)}</label>{loc()}<collectionReference>{coll}</collectionReference><iterationOrder>Asc</iterationOrder>{conn(nxt, "nextValueConnector")}{conn(done, "noMoreValuesConnector")}</loops>')

def lookup(name, label, obj, filters, fields, nxt, first=False, logic='and', sort='CreatedDate'):
    x = f'<recordLookups><name>{name}</name><label>{e(label)}</label>{loc()}<assignNullValuesIfNoRecordsFound>false</assignNullValuesIfNoRecordsFound>{conn(nxt)}<filterLogic>{logic}</filterLogic>'
    for f, op, v in filters:
        x += f'<filters><field>{f}</field><operator>{op}</operator><value>{val(v)}</value></filters>'
    x += f'<getFirstRecordOnly>{"true" if first else "false"}</getFirstRecordOnly><object>{obj}</object>'
    x += ''.join(f'<queriedFields>{f}</queriedFields>' for f in fields)
    if sort:
        x += f'<sortField>{sort}</sortField><sortOrder>Asc</sortOrder>'
    els['recordLookups'].append(x + '<storeOutputAutomatically>true</storeOutputAutomatically></recordLookups>')

def create_one(name, label, obj, assigns, nxt, fault):
    x = f'<recordCreates><name>{name}</name><label>{e(label)}</label>{loc()}{conn(nxt)}{conn(fault, "faultConnector")}'
    for f, v in assigns:
        x += f'<inputAssignments><field>{f}</field><value>{val(v)}</value></inputAssignments>'
    els['recordCreates'].append(x + f'<object>{obj}</object><storeOutputAutomatically>true</storeOutputAutomatically></recordCreates>')

def create_many(name, label, ref, nxt, fault):
    els['recordCreates'].append(f'<recordCreates><name>{name}</name><label>{e(label)}</label>{loc()}{conn(nxt)}{conn(fault, "faultConnector")}<inputReference>{ref}</inputReference></recordCreates>')

def var(name, dtype, desc, coll=False, inp=False, obj=None, default=None, scale=None):
    x = f'<variables><name>{name}</name><description>{e(desc)}</description><dataType>{dtype}</dataType><isCollection>{"true" if coll else "false"}</isCollection><isInput>{"true" if inp else "false"}</isInput><isOutput>false</isOutput>'
    if obj:
        x += f'<objectType>{obj}</objectType>'
    if scale is not None:
        x += f'<scale>{scale}</scale>'
    if default is not None:
        x += f'<value>{val(default)}</value>'
    els['variables'].append(x + '</variables>')

def display(name, html):
    return f'<fields><name>{name}</name><fieldText>{e(html)}</fieldText><fieldType>DisplayText</fieldType></fields>'

def inp(name, dtype, label, required=False, default=None, help=None, rule=None, vis=None, scale=None, choices=None, reset=False):
    ftype = 'DropdownBox' if choices else 'InputField'
    x = f'<fields><name>{name}</name>'
    if choices:
        x += f'<choiceReferences>{choices}</choiceReferences>'
    x += f'<dataType>{dtype}</dataType>'
    if default is not None:
        x += f'<defaultValue>{val(default)}</defaultValue>'
    x += f'<fieldText>{e(label)}</fieldText><fieldType>{ftype}</fieldType>'
    if help:
        x += f'<helpText>{e(help)}</helpText>'
    if reset:
        x += '<inputsOnNextNavToAssocScrn>ResetValues</inputsOnNextNavToAssocScrn>'
    x += f'<isRequired>{"true" if required else "false"}</isRequired>'
    if scale is not None:
        x += f'<scale>{scale}</scale>'
    if rule:
        x += f'<validationRule><errorMessage>{e(rule[0])}</errorMessage><formulaExpression>{e(rule[1])}</formulaExpression></validationRule>'
    if vis:
        x += f'<visibilityRule><conditionLogic>and</conditionLogic>{vis}</visibilityRule>'
    return x + '</fields>'

def screen(name, label, fields, nxt, finish=False, next_label=None):
    x = f'<screens><name>{name}</name><label>{e(label)}</label>{loc()}<allowBack>false</allowBack><allowFinish>true</allowFinish><allowPause>false</allowPause>{conn(nxt)}'
    x += ''.join(fields)
    if next_label:
        x += f'<nextOrFinishButtonLabel>{e(next_label)}</nextOrFinishButtonLabel>'
    els['screens'].append(x + '<showFooter>true</showFooter><showHeader>true</showHeader></screens>')

