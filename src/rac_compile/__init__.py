"""
rac-compile: Compile RAC DSL to standalone JavaScript, Python, and Rust.

This module generates JS, Python, and Rust code from .rac files for use in
browsers, Node.js, Python applications, and Rust binaries without extra runtime
dependencies.
"""

from .compile_model import (
    CompilationError,
    CompileContext,
    CompiledInput,
    CompiledModule,
    CompiledOutput,
    CompiledParameter,
    CompiledVariable,
    FormulaAssignment,
    LoweredComputation,
    LoweredInput,
    LoweredOutput,
    LoweredParameter,
    LoweredProgram,
)
from .harness import (
    HARNESS_CASES,
    HarnessCase,
    HarnessResult,
    HarnessSummary,
    format_harness_summary,
    format_harness_summary_json,
    run_compiler_harness,
)
from .js_generator import JSCodeGenerator
from .js_generator import Parameter as JSParameter
from .js_generator import Variable as JSVariable
from .js_generator import generate_eitc_calculator as generate_eitc_calculator_js
from .module_resolution import (
    ImportResolver,
    ModuleResolutionConfig,
    ModuleResolutionError,
    build_import_resolver,
    discover_module_resolution,
)
from .parameter_bindings import (
    ParameterBinding,
    ParameterBindingError,
    ParameterBundle,
)
from .parser import (
    ExportSpec,
    ImportSpec,
    ImportSymbolSpec,
    ParameterDef,
    ParserError,
    RacFile,
    ReExportSpec,
    SourceBlock,
    TemporalEntry,
    VariableBlock,
    parse_rac,
)
from .program import RacProgram, load_rac_program
from .python_generator import Parameter as PythonParameter
from .python_generator import PythonCodeGenerator
from .python_generator import Variable as PythonVariable
from .python_generator import generate_eitc_calculator as generate_eitc_calculator_py
from .rust_generator import RustCodeGenerator

__version__ = "0.2.0"
__all__ = [
    "JSCodeGenerator",
    "PythonCodeGenerator",
    "RustCodeGenerator",
    "CompileContext",
    "CompilationError",
    "HarnessCase",
    "HarnessResult",
    "HarnessSummary",
    "HARNESS_CASES",
    "ImportResolver",
    "ModuleResolutionConfig",
    "ModuleResolutionError",
    "ParameterBinding",
    "ParameterBindingError",
    "ParameterBundle",
    "RacProgram",
    "CompiledInput",
    "CompiledModule",
    "CompiledParameter",
    "CompiledOutput",
    "CompiledVariable",
    "FormulaAssignment",
    "LoweredComputation",
    "LoweredInput",
    "LoweredOutput",
    "LoweredParameter",
    "LoweredProgram",
    "format_harness_summary",
    "format_harness_summary_json",
    "generate_eitc_calculator_js",
    "generate_eitc_calculator_py",
    "build_import_resolver",
    "discover_module_resolution",
    "JSParameter",
    "JSVariable",
    "PythonParameter",
    "PythonVariable",
    "parse_rac",
    "ImportSpec",
    "ImportSymbolSpec",
    "ExportSpec",
    "RacFile",
    "ReExportSpec",
    "SourceBlock",
    "VariableBlock",
    "ParameterDef",
    "ParserError",
    "TemporalEntry",
    "load_rac_program",
    "run_compiler_harness",
]
