import Create from "./main/create.vue";
import Container from "./main/container.vue";
import vuexModule from "./main/vuex.js";

function setup(app) {
    app.store.registerModule("notebooks", vuexModule);

    app.source.addCreator({
        key: "notebook",
        text: "Notebook",
        icon: "code",
        route: "/create/source/notebook"
    });

    /*
    app.source.addRoute({
      path: "/stream/update",
      component: Update
    });
    */

    app.addRoute({
        path: "/create/source/notebook",
        component: Create
    });

    app.source.addType({
        type: "notebook",
        title: "Notebook",
        list_title: "Notebooks",
        icon: "code"
    });

    // We eliminate the default header, since we will be displaying everything in a single card
    app.source.addComponent({
        component: null, // Header,
        type: "notebook",
        key: "header"
    });

    // Add the notebook card
    app.source.addComponent({
        component: Container,
        type: "notebook",
        key: "view",
        weight: 5
    });
}

export default setup;