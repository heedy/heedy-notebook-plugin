# Heedy Notebook Plugin

This plugin enables use of Jupyter-like notebooks from directly within Heedy. The notebooks are automatically connected to heedy, giving you direct access to all your data. Right now, it is assumed that all users of Heedy are trusted, since the notebooks are not isolated - any user can create a notebook and run arbitrary code!


![Example heedy notebook](./screenshot.png)

## Building

```
git clone https://github.com/heedy/heedy-notebook-plugin
cd heedy-notebook-plugin
make
```

The plugin zip file will be created at `dist/heedy-notebook-plugin-{VERSION}.zip`. It can be installed by uploading to heedy from the UI.

### Developing

To develop the plugin, create a heedy database, run the build in debug mode (which watches files for changes and auto-updates them), and link the build to heedy's plugin directory:

```
heedy create testdb
mkdir testdb/plugins
make debug
# In a different terminal (since make debug watches files):
ln -s $(pwd)/dist/notebook ./testdb/plugins/notebook
```

At this point, you should edit `testdb/heedy.conf` to add the notebook plugin. Any changes you make to the frontend should be available on browser refresh, and any changes to the Python files require a heedy restart. 

