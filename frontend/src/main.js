import Create from "./main/create.vue";
import Container from "./main/container.vue";
import vuexModule from "./main/vuex.js";

function setup(app) {
    app.store.registerModule("notebooks", vuexModule);

    app.object.addCreator({
        key: "notebook",
        title: "Notebook",
        description: "Analyze your data with a Python notebook environment",
        icon: "code",
        route: "/create/object/notebook"
    });

    /*
    app.object.addRoute({
      path: "/stream/update",
      component: Update
    });
    */

    app.addRoute({
        path: "/create/object/notebook",
        component: Create
    });

    app.object.addType({
        type: "notebook",
        title: "Notebook",
        list_title: "Notebooks",
        icon: "code"
    });

    // We eliminate the default header, since we will be displaying everything in a single card
    app.object.addComponent({
        component: null, // Header,
        type: "notebook",
        key: "header"
    });

    // Add the notebook card
    app.object.addComponent({
        component: Container,
        type: "notebook",
        key: "view",
        weight: 5
    });
}

export default setup;