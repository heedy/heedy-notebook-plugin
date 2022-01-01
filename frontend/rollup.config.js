import resolve from "@rollup/plugin-node-resolve";
import commonjs from "@rollup/plugin-commonjs";
import postcss from "rollup-plugin-postcss";
import json from "@rollup/plugin-json";
import VuePlugin from "rollup-plugin-vue";
import replace from "@rollup/plugin-replace";
import {
    terser
} from "rollup-plugin-terser";
import gzipPlugin from "rollup-plugin-gzip";

import glob from "glob";

const plugin_name = "notebook"

const production = !(process.env.NODE_ENV === 'debug');
const plugins = [
    VuePlugin({
        // https://github.com/vuejs/rollup-plugin-vue/issues/238
        needMap: false
    }),
    commonjs(),
    resolve({
        browser: true,
        preferBuiltins: false
    }),
    postcss({
        minimize: production
    }),
    json({
        compact: production
    }),
    replace({
        "process.env.NODE_ENV": JSON.stringify(production ? "production" : "debug"),
    })
];
if (production) {
    plugins.push(terser({
        compress: {
            ecma: 10, // Heedy doesn't do backwards compatibility
            drop_console: true,
        },
        mangle: true,
        module: true
    }));
    plugins.push(gzipPlugin());
} else {
    console.log("Running debug build");
}

function checkExternal(modid, parent, isResolved) {
    return (!isResolved && modid.endsWith(".mjs") && modid.startsWith(".")) || modid.startsWith("http");
}

function out(name, loc = "", format = "es") {
    let filename = name.split(".");
    return {
        input: "src/" + name,
        output: {
            name: filename[0],
            file: `../dist/${plugin_name}/public/static/${plugin_name}/` +
                loc +
                filename[0] +
                (format == "es" ? ".mjs" : ".js"),
            format: format
        },
        plugins: plugins,
        external: checkExternal
    };
}
export default [
    // The base files
    out("main.js")
].concat(glob.sync("dist/*.js", {
    cwd: "./src"
}).map(a => out(a, "../")));