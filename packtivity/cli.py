import click
import packtivity
import os
import jsonschema
import yaml
import capschemas
import logging

log = logging.getLogger(__name__)

#stolen from yadage
def finalize_value(value,context):
    if type(value)==list:
        return [finalize_value(x,context) for x in value]
    if type(value) in [str,unicode]:
        return value.format(**context)
    return value

def finalize_input(json,context):
    context['workdir'] = context['readwrite'][0]
    result = {}
    for k,v in json.iteritems():
        if type(v) is not list:
            result[k] = finalize_value(v,context)
        else:
            result[k] = [finalize_value(element,context) for element in v]
    return result

def getinit_data(initfiles,parameters):
    '''
    get initial data from both a list of files and a list of 'pname=pvalue'
    strings as they are passed in the command line <pvalue> is assumed to be a
    YAML parsable string.
    '''
    initdata = {}
    for initfile in initfiles:
        initdata.update(**yaml.load(open(initfile)))

    for x in parameters:
        key,value = x.split('=')
        initdata[key]=yaml.load(value)
    return initdata

def load_pack(spec,toplevel,schemasource,validate):
    #in case that spec is a json reference string, we will treat it as such
    #if it's just a filename, this should not affect it...
    spec   = capschemas.load(
            {'$ref':spec},
            toplevel,
            'packtivity/packtivity-schema',
            schemadir = schemasource,
            validate = validate,
            initialload = False
    )
    return spec

@click.command()
@click.option('--parameter', '-p', multiple=True)
@click.option('-c','--context', default = None)
@click.option('-w','--workdir', default = os.getcwd())
@click.option('-t','--toplevel', default = os.getcwd())
@click.option('-s','--schemasource', default = capschemas.schemadir)
@click.option('-v','--verbosity', default = 'INFO')
@click.option('--validate/--no-validate', default = True)
@click.argument('spec')
@click.argument('initfiles', nargs = -1)
def runcli(spec,initfiles,parameter,context,workdir,toplevel,schemasource,validate,verbosity):
    logging.basicConfig(level = getattr(logging,verbosity))

    spec = load_pack(spec,toplevel,schemasource,validate)

    parameters = getinit_data(initfiles,parameter)


    workdir = os.path.realpath(workdir)
    ctx    = yaml.load(open(context)) if context else {}
    if 'readwrite' not in ctx:
        ctx['readwrite'] = [workdir]
    else:
        ctx['readwrite'] += [workdir]
    if 'readonly' not in ctx:
        ctx['readonly'] = []

    if 'nametag' not in ctx:
        ctx['nametag'] = 'pack'

    #interpolate parameters out of courtesy
    parameters = finalize_input(parameters,ctx)

    p = packtivity.packtivity_callable(spec,parameters,ctx)
    prepub = p.published_data is not None
    if prepub:
        click.echo(str(p.published_data)+(' (prepublished)' if prepub else ''))

    result = p()
    if not prepub:
        click.echo(result)

@click.command()
@click.argument('spec')
@click.option('-t','--toplevel', default = os.getcwd())
@click.option('-c','--schemasource', default = capschemas.schemadir)
@click.option('-n','--schemaname', default = 'packtivity/packtivity-schema')
def validatecli(spec,toplevel,schemasource,schemaname):
    try:
        spec = load_pack(spec,toplevel,schemasource,validate = True)
    except jsonschema.exceptions.ValidationError as e:
        click.echo(e)
        raise click.ClickException(click.style('packtivity definition not valid',fg = 'red'))
    click.secho('packtivity definition is valid',fg = 'green')
