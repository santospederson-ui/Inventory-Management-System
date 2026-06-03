document.addEventListener("DOMContentLoaded", function () {

    const searchInput = document.getElementById("searchInput");
    const searchForm = document.getElementById("searchForm");

    if (!searchInput || !searchForm) {
        return; // stop if page has no search
    }

    let timer;

    searchInput.addEventListener("keyup", function () {

        clearTimeout(timer);

        timer = setTimeout(function () {

            let value = searchInput.value.trim();

            // If empty → go back to clean page (no search)
            if (value === "") {
                window.location.href = searchForm.action || window.location.pathname;
                return;
            }

            // Otherwise submit search
            searchForm.submit();

        },);

    });

    // Keep cursor in search box after reload
    window.addEventListener("load", function () {
        searchInput.focus();
        searchInput.selectionStart = searchInput.selectionEnd = searchInput.value.length;
    });

});