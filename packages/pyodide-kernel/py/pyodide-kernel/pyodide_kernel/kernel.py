# This is our ipykernel mock
import typing

from .comm import get_comm_manager, CommManager

from IPython.utils.tokenutil import line_at_cursor, token_at_cursor
from pyodide_js import loadPackagesFromImports as _load_packages_from_imports
from traitlets import Any, Instance, default
from traitlets.config import LoggingConfigurable

if typing.TYPE_CHECKING:
    from .interpreter import Interpreter

from .litetransform import LiteTransformerManager

try:
    from IPython.core.completer import provisionalcompleter as _provisionalcompleter
    from IPython.core.completer import rectify_completions as _rectify_completions

    _use_experimental_60_completion = True
except ImportError:
    _use_experimental_60_completion = False


_EXPERIMENTAL_KEY_NAME = "_jupyter_types_experimental"


class PyodideKernel(LoggingConfigurable):
    interpreter: "Interpreter" = Instance("pyodide_kernel.interpreter.Interpreter")
    comm_manager: CommManager = Instance(CommManager)
    parent_header: typing.Any = Instance(Any, allow_none=True)
    lite_transform_manager: LiteTransformerManager = Instance(
        LiteTransformerManager, ()
    )

    @default("comm_manager")
    def _default_comm_manager(self):
        return get_comm_manager()

    def get_parent(self):
        # TODO mimic ipykernel's get_parent signature
        # (take a channel parameter)
        return self._parent_header

    def comm_info(self, target_name=""):
        comms = {}

        for comm_id, comm in self.comm_manager.comms.items():
            if target_name == "" or comm.target_name == target_name:
                comms[comm_id] = dict(target_name=comm.target_name)

        return comms

    def inspect(self, code, cursor_pos, detail_level):
        found = False
        name = token_at_cursor(code, cursor_pos)
        data, results = {}, {}
        try:
            data = self.interpreter.object_inspect_mime(name, detail_level)
            found = True
        except Exception:
            pass

        results["data"] = data
        results["metadata"] = {}
        results["found"] = found
        results["status"] = "ok"

        return results

    def is_complete(self, code):
        transformer_manager = getattr(
            self.interpreter, "input_transformer_manager", None
        )
        if transformer_manager is None:
            transformer_manager = self.interpreter.input_splitter
        status, indent_spaces = transformer_manager.check_complete(code)
        results = {"status": status}
        if status == "incomplete":
            results["indent"] = " " * indent_spaces
        return results

    def complete(self, code, cursor_pos):
        if _use_experimental_60_completion:
            return self._experimental_do_complete(code, cursor_pos)

        if cursor_pos is None:
            cursor_pos = len(code)
        line, offset = line_at_cursor(code, cursor_pos)
        line_cursor = cursor_pos - offset

        txt, matches = self.interpreter.complete("", line, line_cursor)
        return {
            "matches": matches,
            "cursor_end": cursor_pos,
            "cursor_start": cursor_pos - len(txt),
            "metadata": {},
            "status": "ok",
        }

    async def run(self, code):
        self.interpreter._last_traceback = None
        # apply pyodide-specific changes that need to occur before interpreting
        code = await self.lite_transform_manager.transform_cell(code)
        exec_code = self.interpreter.transform_cell(code)

        results = {}

        try:
            await _load_packages_from_imports(exec_code)
        except Exception:
            self.interpreter.showtraceback()
        else:
            if self.interpreter.should_run_async(code):
                await self.interpreter.run_cell_async(code, store_history=True)
            else:
                self.interpreter.run_cell(code, store_history=True)

            results["payload"] = self.interpreter.payload_manager.read_payload()
            self.interpreter.payload_manager.clear_payload()

        if self.interpreter._last_traceback is None:
            results["status"] = "ok"
        else:
            last_traceback = self.interpreter._last_traceback
            results["status"] = "error"
            results["ename"] = last_traceback["ename"]
            results["evalue"] = last_traceback["evalue"]
            results["traceback"] = last_traceback["traceback"]

        return results

    def _experimental_do_complete(self, code, cursor_pos):
        """
        Experimental completions from IPython, using Jedi.
        """
        if cursor_pos is None:
            cursor_pos = len(code)
        with _provisionalcompleter():
            assert self.interpreter is not None
            raw_completions = self.interpreter.Completer.completions(code, cursor_pos)
            completions = list(_rectify_completions(code, raw_completions))

            comps = []
            for comp in completions:
                comps.append(
                    dict(
                        start=comp.start,
                        end=comp.end,
                        text=comp.text,
                        type=comp.type,
                        signature=comp.signature,
                    )
                )

        if completions:
            s = completions[0].start
            e = completions[0].end
            matches = [c.text for c in completions]
        else:
            s = cursor_pos
            e = cursor_pos
            matches = []

        return {
            "matches": matches,
            "cursor_end": e,
            "cursor_start": s,
            "metadata": {_EXPERIMENTAL_KEY_NAME: comps},
            "status": "ok",
        }
