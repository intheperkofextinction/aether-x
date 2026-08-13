from setuptools import setup
from pybind11.setup_helpers import Pybind11Extension, build_ext

ext_modules = [
    Pybind11Extension(
        "aether_cpp_core",
        ["order_book_cpp.cpp"],
        extra_compile_args=["-O3", "-march=native", "-std=c++17"], # Maximum hardware-level optimization
    ),
]

setup(
    name="aether_cpp_core",
    version="1.0.0",
    author="Amal Sudhakar",
    description="C++ Core Execution Engine for Aether-X",
    ext_modules=ext_modules,
    cmdclass={"build_ext": build_ext},
)
