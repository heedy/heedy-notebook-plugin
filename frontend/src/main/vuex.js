import Vue from "../../dist/vue.mjs";
import api from "../../util.mjs";



import updateNotebook, {
    addUpdate,
    deduplicateUpdate
} from "./updateNotebook.js";

export default {
    state: {
        notebooks: {},
        cell_update_dedup: {}
    },
    mutations: {
        setNotebook(state, v) {
            if (state.notebooks.hasOwnProperty(v.id)) {
                Vue.set(state.notebooks[v.id], "notebook", v.notebook);
            } else {
                Vue.set(state.notebooks, v.id, {
                    notebook: v.notebook,
                    updates: [],
                    state: "unknown"
                });
            }
        },
        addNotebookUpdate(state, v) {
            Vue.set(state.notebooks[v.id], "updates", addUpdate(state.notebooks[v.id].updates, v.data));
        },
        undoNotebookUpdates(state, v) {
            if (v.data.cell_id === undefined) {
                Vue.set(state.notebooks[v.id], "updates", state.notebooks[v.id].updates.slice(0, -1));
                return;
            }
            Vue.set(state.notebooks[v.id], "updates", state.notebooks[v.id].updates.filter((u) => u.cell_id != v.data.cell_id));
        },
        applyNotebookUpdates(state, v) {
            if (state.notebooks[v.id] === undefined || state.notebooks[v.id].notebook == null) {
                return; // Don't apply updates to notebooks we're not holding in memory
            }
            let newNotebook = {
                notebook: updateNotebook(state.notebooks[v.id].notebook, v.updates),
                updates: deduplicateUpdate(state.notebooks[v.id].notebook, state.notebooks[v.id].updates, v.updates),
                state: state.notebooks[v.id].state
            };
            if ("clear" in v) {
                newNotebook.updates = []
            }
            Vue.set(state.notebooks, v.id, newNotebook);
        },
        setNotebookKernelState(state, v) {
            if (state.notebooks.hasOwnProperty(v.id)) {
                Vue.set(state.notebooks[v.id], "state", v.state);
            } else {
                Vue.set(state.notebooks, v.id, {
                    notebook: null,
                    updates: [],
                    state: v.state
                });
            }
        },
        setDedup(state, v) {
            Vue.set(state.cell_update_dedup, v.key, v.value);
        },
        clearDedup(state, v) {
            if (state.cell_update_dedup[v.key] !== undefined) {
                let resolve = state.cell_update_dedup[v.key];
                Vue.delete(state.cell_update_dedup, v.key);
                if (resolve != null) {
                    setTimeout(resolve, 0);
                }
            }
        }
    },
    actions: {
        readNotebook: async function ({
            commit
        }, q) {
            let res = await api("GET", `api/objects/${q.id}/notebook`);
            if (res.response.ok) {
                console.vlog(res.data);
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
        saveNotebook: async function ({
            state,
            commit
        }, q) {
            console.vlog("Saving notebook", q.id);
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
                    updates: state.notebooks[q.id].updates // Updates might have already been deduplicated
                });
            }
        },
        getNotebookCellOutput: async function ({
            state,
            commit
        }, q) {
            if (state.notebooks[q.id] === undefined || state.notebooks[q.id].notebook == null) {
                return;
            }
            let dedup_key = `${q.id}/${q.cell_id}`;
            if (state.cell_update_dedup[dedup_key] !== undefined) {
                let dkey = state.cell_update_dedup[dedup_key];
                if (dkey != null) {
                    return; // There is already someone waiting to query, so no need to pile up
                }
                await (new Promise((resolve, reject) => {
                    console.vlog(`Deferring cell read for ${dedup_key}`);
                    commit("setDedup", { key: dedup_key, value: resolve });
                }));
                console.vlog(`Resuming cell read for ${dedup_key}`);
            } else if (q.data.outputs !== undefined) {
                console.vlog(`Using cell output contained in event message for ${dedup_key}`);
                // Outputs were sent in the message itself, so set them directly!
                commit("applyNotebookUpdates", {
                    id: q.id,
                    updates: [q.data]
                });
                return;

            }
            commit("setDedup", { key: dedup_key, value: null });
            let res = await api("GET", `api/objects/${q.id}/notebook/cell/${q.cell_id}`);
            if (!res.response.ok) {
                commit("alert", {
                    type: "error",
                    text: res.data.error_description
                });
                return

            }
            commit("applyNotebookUpdates", {
                id: q.id,
                updates: [res.data]
            });
            commit("clearDedup", { key: dedup_key });

        },
        runNotebookCell: async function ({
            state,
            commit
        }, q) {
            let nb = state.notebooks[q.id].updates;
            if (nb.length > 0) {
                console.vlog("Saving notebook", q.id);
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
                    // clear: true, - the updates should get deduplicated
                    updates: state.notebooks[q.id].updates // Updates might have already been deduplicated
                });
            }

            if (state.notebooks[q.id].notebook[q.data.cell_id].cell_type == "code") {
                console.vlog("Running cell", q.id, q.data);

                let res = await api("POST", `api/objects/${q.id}/notebook/kernel`, q.data);
                if (!res.response.ok) {
                    commit("alert", {
                        type: "error",
                        text: res.data.error_description
                    });

                }
            }

        },
        runNotebook: async function ({
            state,
            commit
        }, q) {
            let nb = state.notebooks[q.id].updates;
            if (nb.length > 0) {
                console.vlog("Saving notebook", q.id);
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
                    // clear: true, - the updates should get deduplicated
                    updates: state.notebooks[q.id].updates // Updates might have already been deduplicated
                });
            }

            let ntb = Object.values(state.notebooks[q.id].notebook);
            ntb.sort((a, b) => a["cell_index"] - b["cell_index"]);
            for (let c of ntb) {
                if (c.cell_type == "code") {
                    console.vlog("Running cell", q.id, c.cell_id);

                    let res = await api("POST", `api/objects/${q.id}/notebook/kernel`, {
                        cell_id: c.cell_id,
                        source: c.source
                    });
                    if (!res.response.ok) {
                        commit("alert", {
                            type: "error",
                            text: res.data.error_description
                        });

                    }
                }
            }

        },
        getNotebookStatus: async function ({
            state,
            commit
        }, q) {
            console.vlog("Getting notebook status for ", q.id);
            let args = {};
            if (q.start !== undefined) {
                args.start = true;
            }

            let res = await api("GET", `api/objects/${q.id}/notebook/kernel`, args);
            if (!res.response.ok) {
                commit("alert", {
                    type: "error",
                    text: res.data.error_description
                });
                return;
            }
            commit("setNotebookKernelState", {
                id: q.id,
                state: res.data
            });
        },
        interruptNotebook: async function ({
            state,
            commit
        }, q) {
            console.vlog("Stopping kernel for", q.id);

            let res = await api("PATCH", `api/objects/${q.id}/notebook/kernel`);
            if (!res.response.ok) {
                commit("alert", {
                    type: "error",
                    text: res.data.error_description
                });

            }
        },
        stopNotebook: async function ({
            state,
            commit
        }, q) {
            console.vlog("Stopping kernel for", q.id);
            let res = await api("DELETE", `api/objects/${q.id}/notebook/kernel`);
            if (!res.response.ok) {
                commit("alert", {
                    type: "error",
                    text: res.data.error_description
                });

            }
        }
    }
}