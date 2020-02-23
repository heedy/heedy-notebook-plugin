import Vue from "../../dist/vue.mjs";
import api from "../../api.mjs";



import updateNotebook, {
    addUpdate
} from "./updateNotebook.js";

export default {
    state: {
        notebooks: {}
    },
    mutations: {
        setNotebook(state, v) {
            if (state.notebooks.hasOwnProperty(v.id)) {
                Vue.set(state.notebooks[v.id], "notebook", v.notebook);
            } else {
                Vue.set(state.notebooks, v.id, {
                    notebook: v.notebook,
                    updates: []
                });
            }
        },
        addNotebookUpdate(state, v) {
            Vue.set(state.notebooks[v.id], "updates", addUpdate(state.notebooks[v.id].updates, v.data));
        },
        applyNotebookUpdates(state, v) {
            let newNotebook = {
                notebook: updateNotebook(state.notebooks[v.id].notebook, v.updates),
                updates: state.notebooks[v.id].updates
            };
            if ("clear" in v) {
                newNotebook.updates = []
            }
            Vue.set(state.notebooks, v.id, newNotebook);
        }
    },
    actions: {
        readNotebook: async function ({
            commit
        }, q) {
            let res = await api("GET", `api/objects/${q.id}/notebook`);
            if (res.response.ok) {
                console.log(res.data);
                commit("setNotebook", {
                    id: q.id,
                    notebook: res.data.reduce((o, v) => {
                        o[v.cell_id] = v;
                        return o
                    }, {})
                })
            }
            if (q.hasOwnProperty("callback")) {
                q.callback();
            }
        },
        /*
        addNotebookCell: async function ({
            state,
            commit
        }, q) {
            console.log("Adding cell", q);
            let res = await api("POST", `api/objects/${q.objectid}/notebook`, q.source);
            if (!res.response.ok) {
                commit("alert", {
                    type: "error",
                    text: res.data.error_description
                });

            }
        },
        */
        saveNotebook: async function ({
            state,
            commit
        }, q) {
            console.log("Saving notebook", q.id);
            let nb = state.notebooks[q.id].updates;

            let res = await api("POST", `api/objects/${q.id}/notebook`, nb);
            if (!res.response.ok) {
                commit("alert", {
                    type: "error",
                    text: res.data.error_description
                });

            } else {
                commit("applyNotebookUpdates", {
                    id: q.id,
                    clear: true,
                    updates: nb
                });
            }
        },
        runNotebookCell: async function ({
            state,
            commit
        }, q) {
            let nb = state.notebooks[q.id].updates;
            if (nb.length > 0) {
                console.log("Saving notebook", q.id);
                let res = await api("POST", `api/objects/${q.id}/notebook`, nb);
                if (!res.response.ok) {
                    commit("alert", {
                        type: "error",
                        text: res.data.error_description
                    });
                    return

                }
                commit("applyNotebookUpdates", {
                    id: q.id,
                    clear: true,
                    updates: nb
                });
            }


            console.log("Running cell", q.id);
            console.log(q.data);

            let res = await api("POST", `api/objects/${q.id}/notebook/${q.data.cell_id}`, q.data);
            if (!res.response.ok) {
                commit("alert", {
                    type: "error",
                    text: res.data.error_description
                });

            }
        },

    }
}