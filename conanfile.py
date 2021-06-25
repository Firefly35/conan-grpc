from conans import ConanFile, CMake, tools
from conans.errors import ConanInvalidConfiguration
from conans.tools import Version
import os


class grpcConan(ConanFile):
    name = "grpc"
    description = "Google's RPC (remote procedure call) library and framework."
    topics = ("conan", "grpc", "rpc")
    url = "https://github.com/conan-io/conan-center-index"
    homepage = "https://github.com/grpc/grpc"
    license = "Apache-2.0"
    exports_sources = ["CMakeLists.txt", "cmake/*"]
    generators = "cmake", "cmake_find_package", "cmake_find_package_multi"
    short_paths = True

    settings = "os", "arch", "compiler", "build_type"
    # TODO: Add deps_source_package option to support grpc dependencies as module and to forward compiler.cppstd and other settings to dependencies
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "codegen": [True, False],
        "csharp_ext": [True, False],
        "cpp_plugin": [True, False],
        "csharp_plugin": [True, False],
        "node_plugin": [True, False],
        "objective_c_plugin": [True, False],
        "php_plugin": [True, False],
        "python_plugin": [True, False],
        "ruby_plugin": [True, False]
    }
    default_options = {
        "shared":  False,
        "fPIC": True,
        "codegen": True,
        "csharp_ext": False,
        "cpp_plugin": True,
        "csharp_plugin": True,
        "node_plugin": True,
        "objective_c_plugin": True,
        "php_plugin": True,
        "python_plugin": True,
        "ruby_plugin": True,
    }

    exports = ['patches/*']
    _cmake = None

    @property
    def _source_subfolder(self):
        return "source_subfolder"
    
    @property
    def _build_subfolder(self):
        return "build_subfolder"


    def requirements(self):
        if not self.options.shared:
            self.requires('zlib/1.2.11')
            self.requires('openssl/1.1.1k')
            self.requires('protobuf/3.15.5')
            self.requires('c-ares/1.17.1')
            self.requires('abseil/20210324.0')
            self.requires('re2/20210202')

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.settings.compiler == "Visual Studio":
            compiler_version = tools.Version(self.settings.compiler.version)
            if compiler_version < 14:
                raise ConanInvalidConfiguration("gRPC can only be built with Visual Studio 2015 or higher.")

    def source(self):
        if self.options.shared:
            self.run("git clone  --recurse-submodules -b v" + self.version + " https://github.com/grpc/grpc " + self._source_subfolder)
            cmake_path = os.path.join(self._source_subfolder, "CMakeLists.txt")
            for patch in self.conan_data["patches"].get(self.version, []):
                tools.patch(**patch)
        else:
            tools.get(**self.conan_data["sources"][self.version])
            extracted_dir = self.name + "-" + self.version
            os.rename(extracted_dir, self._source_subfolder)
            cmake_path = os.path.join(self._source_subfolder, "CMakeLists.txt")
            # See #5
            tools.replace_in_file(cmake_path, "_gRPC_PROTOBUF_LIBRARIES", "CONAN_LIBS_PROTOBUF")

    def _configure_cmake(self):
        if self._cmake is not None:
            return self._cmake

        # This doesn't work yet as one would expect, because the install target builds everything
        # and we need the install target because of the generated CMake files
        #
        #   enable_mobile=False # Enables iOS and Android support
        #
        # cmake.definitions["CONAN_ENABLE_MOBILE"] = "ON" if self.options.build_csharp_ext else "OFF"
        
        
        self._cmake = CMake(self)

        self._cmake.definitions["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"

        self._cmake.definitions["gRPC_BUILD_CODEGEN"] = self.options.codegen
        self._cmake.definitions["gRPC_BUILD_CSHARP_EXT"] = self.options.csharp_ext
        self._cmake.definitions["gRPC_BUILD_TESTS"] = False

        # We need the generated cmake/ files (bc they depend on the list of targets, which is dynamic)
        self._cmake.definitions["gRPC_INSTALL"] = True

        # tell grpc to use the find_package versions
        # the module version fails with gRPC_ABSL_PROVIDER is "module" but ABSL_ROOT_DIR is wrong
        self._cmake.definitions["gRPC_ABSL_PROVIDER"] = "module" if self.options.shared else "package"
        self._cmake.definitions["gRPC_CARES_PROVIDER"] = "module" if self.options.shared else "package"
        self._cmake.definitions["gRPC_ZLIB_PROVIDER"] = "module" if self.options.shared else "package"
        self._cmake.definitions["gRPC_SSL_PROVIDER"] = "module" if self.options.shared else "package"
        self._cmake.definitions["gRPC_PROTOBUF_PROVIDER"] = "module" if self.options.shared else "package"
        self._cmake.definitions["gRPC_RE2_PROVIDER"] = "module" if self.options.shared else "package"

        self._cmake.definitions["gRPC_BUILD_GRPC_CPP_PLUGIN"] = self.options.cpp_plugin
        self._cmake.definitions["gRPC_BUILD_GRPC_CSHARP_PLUGIN"] = self.options.csharp_plugin
        self._cmake.definitions["gRPC_BUILD_GRPC_NODE_PLUGIN"] = self.options.node_plugin
        self._cmake.definitions["gRPC_BUILD_GRPC_OBJECTIVE_C_PLUGIN"] = self.options.objective_c_plugin
        self._cmake.definitions["gRPC_BUILD_GRPC_PHP_PLUGIN"] = self.options.php_plugin
        self._cmake.definitions["gRPC_BUILD_GRPC_PYTHON_PLUGIN"] = self.options.python_plugin
        self._cmake.definitions["gRPC_BUILD_GRPC_RUBY_PLUGIN"] = self.options.ruby_plugin

        self._cmake.definitions["protobuf_DEBUG_POSTFIX"] = ""

        # see https://github.com/inexorgame/conan-grpc/issues/39
        if self.settings.os == "Windows":
            if not self.options["protobuf"].shared:
                self._cmake.definitions["Protobuf_USE_STATIC_LIBS"] = "ON"
            else:
                self._cmake.definitions["PROTOBUF_USE_DLLS"] = "ON"

        self._cmake.configure(build_folder=self._build_subfolder)
        return self._cmake

    def build(self):
 #       for patch in self.conan_data["patches"].get(self.version, []):
 #           tools.patch(**patch)
        cmake = self._configure_cmake()
        cmake.build()

    def package(self):
        self.copy(pattern="LICENSE", dst="licenses", src=self._source_subfolder)
        cmake = self._configure_cmake()
        cmake.install()

        tools.rmdir(os.path.join(self.package_folder, "lib", "cmake"))
        tools.rmdir(os.path.join(self.package_folder, "lib", "pkgconfig"))
        tools.rmdir(os.path.join(self.package_folder, "share"))

        self.copy(pattern="LICENSE", dst="licenses", src=self._source_subfolder)
        self.copy(pattern="*.cmake", dst=os.path.join("lib", "cmake"), src=os.path.join(self.source_folder, "cmake"))
    
    def package_info(self):
        bindir = os.path.join(self.package_folder, "bin")
        self.output.info("Appending PATH environment variable: {}".format(bindir))
        self.env_info.PATH.append(bindir)

        self.cpp_info.names["cmake_find_package"] = "gRPC"
        self.cpp_info.names["cmake_find_package_multi"] = "gRPC"
        if not self.options.shared:
            self.cpp_info.libs = [
                "grpc++_unsecure",
                "grpc++_reflection",
                "grpc++_error_details",
                "grpc++",
                "grpc_unsecure",
                "grpc_plugin_support",
                "grpcpp_channelz",
                "grpc",
                "gpr",
                "address_sorting",
                "upb",
            ]
        else:
            self.cpp_info.libs = [
                "grpc++_unsecure",
                "grpc++_reflection",
                "grpc++_error_details",
                "grpc++",
                "grpc_unsecure",
                "grpc_plugin_support",
                "grpcpp_channelz",
                "grpc",
                "protobuf",
                "address_sorting",
                "re2",
                "upb",
                "cares",
                "z",
                "absl_raw_hash_set",
                "absl_hashtablez_sampler",
                "absl_exponential_biased",
                "absl_hash",
                "absl_bad_variant_access",
                "absl_city",
                "absl_status",
                "absl_cord",
                "absl_bad_optional_access",
                "absl_str_format_internal",
                "absl_synchronization",
                "absl_graphcycles_internal",
                "absl_symbolize",
                "absl_demangle_internal",
                "absl_stacktrace",
                "absl_debugging_internal",
                "absl_malloc_internal",
                "absl_time",
                "absl_time_zone",
                "absl_civil_time",
                "absl_strings",
                "absl_strings_internal",
                "absl_throw_delegate",
                "absl_int128",
                "absl_base",
                "absl_spinlock_wait",
                "absl_raw_logging_internal",
                "absl_log_severity",
                "ssl",
                "crypto",
                "gpr",
                "pthread",
            ]


        _system_libs = []
        if self.settings.os in ["Macos", "Linux"]:
            _system_libs = ['m', 'pthread']
        elif self.settings.os == 'Windows':
            _system_libs = ['wsock32', 'ws2_32', 'crypt32']

        # gRPC::address_sorting
        self.cpp_info.components["address_sorting"].names["cmake_find_package"] = "address_sorting"
        self.cpp_info.components["address_sorting"].names["cmake_find_package_multi"] = "address_sorting"
        self.cpp_info.components["address_sorting"].system_libs = _system_libs
        self.cpp_info.components["address_sorting"].libs = ["address_sorting"]
        
        # gRPC::gpr
        self.cpp_info.components["gpr"].names["cmake_find_package"] = "gpr"
        self.cpp_info.components["gpr"].names["cmake_find_package_multi"] = "gpr"
        self.cpp_info.components["gpr"].requires = ["abseil::absl_base", "abseil::absl_memory", "abseil::absl_status", "abseil::absl_str_format", "abseil::absl_strings", "abseil::absl_synchronization", "abseil::absl_time", "abseil::absl_optional"]
        if self.settings.os in ['Linux', 'Macos']:
            self.cpp_info.components["gpr"].system_libs = _system_libs
        self.cpp_info.components["gpr"].libs = ["gpr"]

        # gRPC::grpc
        self.cpp_info.components["_grpc"].names["cmake_find_package"] = "grpc"
        self.cpp_info.components["_grpc"].names["cmake_find_package_multi"] = "grpc"
        self.cpp_info.components["_grpc"].requires = ["zlib::zlib", "c-ares::cares", "address_sorting", "re2::re2", "upb", "abseil::absl_flat_hash_map", "abseil::absl_inlined_vector", "abseil::absl_bind_front", "abseil::absl_statusor", "gpr", "openssl::ssl", "openssl::crypto", "address_sorting", "upb"]
        self.cpp_info.components["_grpc"].frameworks = ["CoreFoundation"]
        self.cpp_info.components["_grpc"].system_libs = _system_libs
        self.cpp_info.components["_grpc"].libs = ["grpc"]
            
        # gRPC::grpc_unsecure
        self.cpp_info.components["grpc_unsecure"].names["cmake_find_package"] = "grpc_unsecure"
        self.cpp_info.components["grpc_unsecure"].names["cmake_find_package_multi"] = "grpc_unsecure"
        self.cpp_info.components["grpc_unsecure"].requires = ["zlib::zlib", "c-ares::cares", "address_sorting", "re2::re2", "upb", "abseil::absl_flat_hash_map", "abseil::absl_inlined_vector", "abseil::absl_statusor", "gpr", "address_sorting", "upb"]
        self.cpp_info.components["grpc_unsecure"].frameworks = ["CoreFoundation"]
        self.cpp_info.components["grpc_unsecure"].system_libs = _system_libs
        self.cpp_info.components["grpc_unsecure"].libs = ["grpc_unsecure"]
        
        # gRPC::grpc++
        self.cpp_info.components["grpc++"].names["cmake_find_package"] = "grpc++"
        self.cpp_info.components["grpc++"].names["cmake_find_package_multi"] = "grpc++"
        self.cpp_info.components["grpc++"].requires = ["protobuf::libprotobuf", "_grpc"]
        self.cpp_info.components["grpc++"].system_libs = _system_libs
        self.cpp_info.components["grpc++"].libs = ["grpc++"]
        
        # gRPC::grpc++_alts
        self.cpp_info.components["grpc++_alts"].names["cmake_find_package"] = "grpc++_alts"
        self.cpp_info.components["grpc++_alts"].names["cmake_find_package_multi"] = "grpc++_alts"
        self.cpp_info.components["grpc++_alts"].requires = ["protobuf::libprotobuf", "grpc++"]
        self.cpp_info.components["grpc++_alts"].system_libs = _system_libs
        self.cpp_info.components["grpc++_alts"].libs = ["grpc++_alts"]
        
        # gRPC::grpc++_error_details
        self.cpp_info.components["grpc++_error_details"].names["cmake_find_package"] = "grpc++_error_details"
        self.cpp_info.components["grpc++_error_details"].names["cmake_find_package_multi"] = "grpc++_error_details"
        self.cpp_info.components["grpc++_error_details"].requires = ["protobuf::libprotobuf", "grpc++"]
        if self.settings.os in ['Macos', 'Linux']:
            self.cpp_info.components["grpc++_error_details"].system_libs = _system_libs
        self.cpp_info.components["grpc++_error_details"].libs = ["grpc++_error_details"]
        
        # gRPC::grpc++_reflection
        self.cpp_info.components["grpc++_reflection"].names["cmake_find_package"] = "grpc++_reflection"
        self.cpp_info.components["grpc++_reflection"].names["cmake_find_package_multi"] = "grpc++_reflection"
        self.cpp_info.components["grpc++_reflection"].requires = ["protobuf::libprotobuf", "grpc++"]
        if self.settings.os in ['Macos', 'Linux']:
            self.cpp_info.components["grpc++_reflection"].system_libs = _system_libs
        self.cpp_info.components["grpc++_reflection"].libs = ["grpc++_reflection"]
        
        # gRPC::grpc++_unsecure
        self.cpp_info.components["grpc++_unsecure"].names["cmake_find_package"] = "grpc++_unsecure"
        self.cpp_info.components["grpc++_unsecure"].names["cmake_find_package_multi"] = "grpc++_unsecure"
        self.cpp_info.components["grpc++_unsecure"].requires = ["protobuf::libprotobuf", "grpc_unsecure"]
        self.cpp_info.components["grpc++_unsecure"].system_libs = _system_libs
        self.cpp_info.components["grpc++_unsecure"].libs = ["grpc++_unsecure"]
        
        # gRPC::grpc_plugin_support
        self.cpp_info.components["grpc_plugin_support"].names["cmake_find_package"] = "grpc_plugin_support"
        self.cpp_info.components["grpc_plugin_support"].names["cmake_find_package_multi"] = "grpc_plugin_support"
        self.cpp_info.components["grpc_plugin_support"].requires = ["protobuf::libprotoc", "protobuf::libprotobuf"]
        if self.settings.os in ['Macos', 'Linux']:
            self.cpp_info.components["grpc_plugin_support"].system_libs = _system_libs
        self.cpp_info.components["grpc_plugin_support"].libs = ["grpc_plugin_support"]
        
        # gRPC::grpcpp_channelz
        self.cpp_info.components["grpcpp_channelz"].names["cmake_find_package"] = "grpcpp_channelz"
        self.cpp_info.components["grpcpp_channelz"].names["cmake_find_package_multi"] = "grpcpp_channelz"
        if self.settings.os in ['Macos', 'Linux']:
            self.cpp_info.components["grpcpp_channelz"].requires = ["protobuf::libprotobuf",  "_grpc"]
            self.cpp_info.components["grpcpp_channelz"].system_libs = _system_libs
        elif self.settings.os in ['Windows']:
            self.cpp_info.components["grpcpp_channelz"].requires = ["protobuf::libprotobuf",  "grpc++"]
        self.cpp_info.components["grpcpp_channelz"].libs = ["grpcpp_channelz"]
        
        # gRPC::upb
        self.cpp_info.components["upb"].names["cmake_find_package"] = "upb"
        self.cpp_info.components["upb"].names["cmake_find_package_multi"] = "upb"
        if self.settings.os in ['Macos', 'Linux']:
            self.cpp_info.components["upb"].system_libs = _system_libs
        self.cpp_info.components["upb"].libs = ["upb"]
        
        # Executables
        # gRPC::grpc_cpp_plugin
        if self.options.cpp_plugin:
            module_target_rel_path = os.path.join("lib", "cmake", "grpc_cpp_plugin.cmake")
            self.cpp_info.components["execs"].build_modules["cmake_find_package"] = [module_target_rel_path]
            self.cpp_info.components["execs"].build_modules["cmake_find_package_multi"] = [module_target_rel_path]

