# Heedy Notebook Plugin

This plugin enables use of Jupyter-like notebooks from directly within Heedy. The notebooks are automatically connected to heedy, giving you direct access to all your data. Right now, it is assumed that all users of Heedy are trusted, since the notebooks are not isolated - any user can create a notebook and run arbitrary code!

![Example heedy notebook](./screenshots/1.png)

## Usage

The plugin can be installed by downloading the release zip file from the releases page, and uploading to heedy from the "plugins" page. The server will take several minutes to restart when enabling the plugin, since it needs to install all of Jupyter's dependencies.

Once the plugin is installed, go to your user's page and create a new object (big plus button). There will be an option of creating a notebook. After creating the notebook, it can be used right away with the `h` variable being your user.

A tutorial on usage of the client [can be seen here](https://heedy.org/python/tutorial.html). For example:

```python
h.objects() # list the objects
myts = h.objects(type="timeseries")[0] # Get a timeseries
myts[:] # Read all the data in the timeseries

myts(t1="now-1d") # Read the data within the past day
```

When accessing heedy from a notebook, you are accessing the database as the `notebook` app, so you will have only the permissions scopes that are available to the app. You can modify these permissions by editing them in the notebook app. By default, your notebooks have full access to all your objects, and have read access to your user.

## Building

```
git clone https://github.com/heedy/heedy-notebook-plugin
cd heedy-notebook-plugin
make
```

The plugin zip file will be created at `dist/heedy-notebook-plugin-{VERSION}.zip`. It can be installed by uploading to heedy from the UI.

### Developing

The plugin is based on the [heedy-template-plugin](https://github.com/heedy/heedy-template-plugin), so general structure and command usage is identical.
