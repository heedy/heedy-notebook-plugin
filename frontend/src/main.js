import Create from "./main/create.vue";
import Update from "./main/update.vue";
import Container from "./main/container.vue";
import vuexModule from "./main/vuex.js";

function setup(app) {
    app.store.registerModule("notebooks", vuexModule);

    app.objects.addCreator({
        key: "notebook",
        title: "Notebook",
        description: "Analyze your data with a Python notebook environment",
        icon: "code",
        route: "/create/object/notebook"
    });

    app.addRoute({
        path: "/create/object/notebook",
        component: Create
    });
    app.objects.addRoute({
        path: "/notebook/update",
        component: Update
    });

    app.objects.setType({
        type: "notebook",
        title: "Notebook",
        list_title: "Notebooks",
        icon: "code"
    });

    // We eliminate the default header, since we will be displaying everything in a single card
    app.objects.addComponent({
        component: null, // Header,
        type: "notebook",
        key: "header"
    });



    // Add the notebook card
    app.objects.addComponent({
        component: Container,
        type: "notebook",
        key: "body",
        weight: 5
    });

    if (app.info.user != null) {
        // Finally, subscribe to notebook events for our own user
        app.websocket.subscribe("notebook_cell_update", {
            event: "notebook_cell_update",
            user: app.info.user.username
        }, (e) => app.store.commit("applyNotebookUpdates", {
            id: e.object,
            updates: [e.data]
        }));
        app.websocket.subscribe("notebook_cell_delete", {
            event: "notebook_cell_delete",
            user: app.info.user.username
        }, (e) => app.store.commit("applyNotebookUpdates", {
            id: e.object,
            updates: [{
                ...e.data,
                delete: true
            }]
        }));
        app.websocket.subscribe("notebook_cell_outputs", {
            event: "notebook_cell_outputs",
            user: app.info.user.username
        }, (e) => app.store.dispatch("getNotebookCellOutput", {
            id: e.object,
            cell_id: e.data.cell_id,
            data: e.data
        }));
        app.websocket.subscribe("notebook_kernel_state", {
            event: "notebook_kernel_state",
            user: app.info.user.username
        }, (e) => app.store.commit("setNotebookKernelState", {
            id: e.object,
            state: e.data.state
        }));
    }

}

export default setup;