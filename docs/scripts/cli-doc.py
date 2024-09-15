# Nicked from md-click which is not maintained anymore. Seems like there
# is a pin of click version on md-click and so we do our own here
#
# We make small changes to ensure the multiline strings are well indented
# all long and short options are separated by `/` rather than new line
import importlib
import pathlib
import textwrap

import click

md_base_template = """
# gitlab-activity

{description}

## Usage

```
{usage}
```

## Options

{options}

## CLI Help

```
{help}
```

"""


def recursive_help(cmd, parent=None):
    ctx = click.core.Context(cmd, info_name=cmd.name, parent=parent)

    yield {
        "command": cmd,
        "help": cmd.get_help(ctx),
        "parent": parent.info_name if parent else '',
        "usage": cmd.get_usage(ctx),
        "params": cmd.get_params(ctx),
        "options": cmd.collect_usage_pieces(ctx),
    }

    commands = getattr(cmd, 'commands', {})
    for sub in commands.values():
        for helpdct in recursive_help(sub, ctx):
            yield from helpdct


def dump_helper(base_command, docs_dir):
    """Dumping help usage files from Click Help files into an md"""
    docs_path = pathlib.Path(docs_dir)
    for helpdct in recursive_help(base_command):
        command = helpdct.get("command")
        helptxt = helpdct.get("help")
        usage = helpdct.get("usage")
        parent = helpdct.get("parent", "") or ''
        options = {
            opt.name: {
                "usage": '/'.join(opt.opts),
                "prompt": opt.prompt,
                "required": opt.required,
                "default": opt.default,
                "help": textwrap.indent(opt.help, prefix='  '),
                "type": str(opt.type),
            }
            for opt in helpdct.get('params', [])
        }
        full_command = f"{str(parent) + ' ' if parent else ''}{command.name!s}"

        md_template = md_base_template.format(
            command_name=full_command,
            description=command.help,
            usage=usage,
            options="\n".join(
                [
                    f"- `{opt_name}`{' (REQUIRED)' if opt.get('required') else ''}:\n"
                    f"  - Type: `{opt.get('type')}`\n"
                    f"  - Default: `{str(opt.get('default')).lower()}`\n"
                    f"  - Usage: `{opt.get('usage')}`\n"
                    "\n"
                    f"{opt.get('help') or ''}\n"
                    for opt_name, opt in options.items()
                ]
            ),
            help=helptxt,
        )

        if not docs_path.exists():
            # Create md file dir if needed
            docs_path.mkdir(parents=True, exist_ok=False)

        md_file_path = docs_path.joinpath(
            full_command.replace(' ', '-').lower() + '.md'
        ).absolute()

        # Create the file per each command
        md_file_path.write_text(md_template, encoding='utf-8')


@click.group()
def cli():
    pass


@cli.command('dumps')
@click.option(
    '--baseModule', help='The base command module path to import', required=True
)
@click.option(
    '--baseCommand', help='The base command function to import', required=True
)
@click.option(
    '--docsPath', help='The docs dir path to write the md files', required=True
)
def dumps(**kwargs):
    """
    # Click-md
    Create md files per each command, in format of `parent-command`,
    under the `--docsPath` directory.
    """
    base_module = kwargs.get('basemodule')
    base_command = kwargs.get('basecommand')
    docs_path = kwargs.get('docspath')

    click.secho(
        f'Creating a new documents from {base_module}.{base_command} into {docs_path}',
        color='green',
    )

    try:
        # Import the module
        module_ = importlib.import_module(base_module)
    except Exception as e:
        click.echo(f'Could not find module: {base_module}. Error: {e!s}')
        return

    try:
        # Import the base command (group of command) function inside the module
        command_ = getattr(module_, base_command)
    except Exception as e:
        click.echo(
            f'Could not find command {base_command} on module {base_module}: {e!s}'
        )
        return

    try:
        dump_helper(command_, docs_dir=docs_path)
        click.secho(f'Created docs under {docs_path}', color='green')
    except Exception as e:
        click.secho(f'Dumps command failed: {e!s}', color='red')
        raise

    return


if __name__ == '__main__':
    cli.add_command(cli)
    cli()
