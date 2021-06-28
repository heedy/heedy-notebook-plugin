export function addUpdate(changeList, change) {
    // We first try adding the change to the most recent element of the changeList, and if we can't,
    // then append the change
    if ("modified" in change) { // Clean up possible "modified"
        change = {
            ...change
        };
        delete change["modified"];
    }
    if ("outputs" in change && change["outputs"].length > 0) { // Clean up possible "outputs"
        change = {
            ...change
        };
        delete change["outputs"];
    }
    if (changeList.length == 0) return [change];
    changeList = [...changeList];
    if (changeList[changeList.length - 1].cell_id == change.cell_id) {
        changeList[changeList.length - 1] = {
            ...changeList[changeList.length - 1],
            ...change
        };
        return changeList;
    }
    changeList.push(change);
    return changeList;
}

// https://gist.github.com/nicbell/6081098
function cmpobj(obj1, obj2) {
    //Loop through properties in object 1
    for (var p in obj1) {
        //Check property exists on both objects
        if (obj1.hasOwnProperty(p) !== obj2.hasOwnProperty(p)) return false;

        switch (typeof (obj1[p])) {
            //Deep compare objects
            case 'object':
                if (!Object.compare(obj1[p], obj2[p])) return false;
                break;
                //Compare function code
            case 'function':
                if (typeof (obj2[p]) == 'undefined' || (p != 'compare' && obj1[p].toString() != obj2[p].toString())) return false;
                break;
                //Compare values
            default:
                if (obj1[p] != obj2[p]) return false;
        }
    }

    //Check object 2 for any extra properties
    for (var p in obj2) {
        if (typeof (obj1[p]) == 'undefined') return false;
    }
    return true;
};

export function deduplicateUpdate(notebook, changeList, appliedChanges) {
    // See if the applied changes match the changeList, and remove from changeList if so
    let i = 0;
    for (let i = 0; i < appliedChanges.length && i < changeList.length; i++) {
        for (let key of Object.keys(changeList[i])) {
            if (key != "outputs") {
                let ac = appliedChanges[i];
                if (ac[key] === undefined) {
                    return changeList.slice(i, changeList.length);
                }
                if (!cmpobj(ac[key], changeList[i][key])) {
                    return changeList.slice(i, changeList.length);
                }
            }

        }
    }

    if (changeList.length < appliedChanges.length) {
        return [];
    }
    return changeList.slice(appliedChanges.length, changeList.length);
}

export default function updateNotebook(notebook, changeList, markModified = false) {
    // updateNotebook gets the object representing the notebook, and returns the equivalent object
    // with the given modifictions applied.
    if (changeList.length == 0) {
        return notebook;
    }
    let cellNumber = Object.keys(notebook).length;

    // Create a quick copy of the root object, so we can just modify the relevant elements
    notebook = {
        ...notebook
    };
    //console.log("START UPDATE", notebook);
    for (let i = 0; i < changeList.length; i++) {
        let c = changeList[i];
        let cell_id = c["cell_id"];
        //console.log("Updating", cell_id)
        if (c.hasOwnProperty("delete") && c["delete"]) {
            if (cell_id in notebook) {

                let cell_index = notebook[cell_id].cell_index;
                delete notebook[cell_id];
                cellNumber--;
                Object.keys(notebook).forEach((k) => {
                    let k_index = notebook[k]["cell_index"];
                    if (k_index >= cell_index) {
                        notebook[k] = {
                            ...notebook[k],
                            cell_index: k_index - 1
                        };
                    }
                });
            } else {
                console.warn("Delete of non-existent cell ID", cell_id);
            }

        } else {
            //console.log("hey", notebook, cell_id in notebook)
            // Now, we check if the cell exists. If not, we create a new one at the given index. If it does, we update it.
            if (cell_id in notebook) {
                //console.log("Cell existss")
                // The cell already exists. First, update the cell to the newest values
                let old_index = notebook[cell_id].cell_index;
                let new_index = c.cell_index || notebook[cell_id].cell_index;
                notebook[cell_id] = {
                    ...notebook[cell_id],
                    ...c
                }

                // Then, update the indices if necessary
                if (old_index > new_index) {
                    Object.keys(notebook).forEach((k) => {
                        if (k == cell_id) return;

                        let k_index = notebook[k]["cell_index"];
                        if (k_index < old_index && k_index >= new_index) {
                            notebook[k] = {
                                ...notebook[k],
                                cell_index: k_index + 1
                            };
                        }
                    });
                } else if (old_index < new_index) {
                    Object.keys(notebook).forEach((k) => {
                        if (k == cell_id) return;

                        let k_index = notebook[k]["cell_index"];
                        if (k_index <= new_index && k_index > old_index) {
                            notebook[k] = {
                                ...notebook[k],
                                cell_index: k_index - 1
                            };
                        }
                    });
                }
            } else {
                // The cell doesn't exist, so add it
                notebook[cell_id] = {
                    cell_id: cell_id,
                    source: "",
                    metadata: {},
                    outputs: [],
                    cell_index: cellNumber,
                    cell_type: "code",
                    ...c
                }
                if (notebook[cell_id].cell_index < cellNumber) {
                    // We need to shift cells after current index
                    let cell_index = notebook[cell_id].cell_index;
                    Object.keys(notebook).forEach((k) => {
                        if (k == cell_id) return;

                        let k_index = notebook[k]["cell_index"];
                        if (k_index >= cell_index) {
                            notebook[k] = {
                                ...notebook[k],
                                cell_index: k_index + 1
                            };
                        }
                    });
                }

                cellNumber++;
            }

            // Mark the cell as modified
            if (markModified) {
                notebook[cell_id].modified = true;
            }
        }
    }
    return notebook;
}