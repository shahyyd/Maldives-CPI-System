window.addEventListener("load", function () {
    const islandSelect = document.getElementById("id_island");

    if (!islandSelect) {
        console.log("Island dropdown not found");
        return;
    }

    islandSelect.addEventListener("change", function () {
        const islandId = islandSelect.value;
        const url = new URL(window.location.href);

        if (islandId) {
            url.searchParams.set("island", islandId);
        } else {
            url.searchParams.delete("island");
        }

        window.location.href = url.toString();
    });
});