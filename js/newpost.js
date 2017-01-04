/**
* @description Populates the modal-body inputs with values from post
*/
$(document).on("click", ".open-PreviewDialog", function () {
     var postContent = $("#content").val();
     var postTitle = $("#title").val();
     postContent = postContent.replace(/(?:\r\n|\r|\n)/g, "<br />");;

     $(".modal-body #post-content-prev").html( postContent );
     $(".modal-body #post-title-prev").html( postTitle );
});

/**
* @description Comfirms the deletion of a post.
* @returns {boolean} false if user didn't click OK in confirm box
*/
function confirmDelete() {
    if (confirm("Post will be deleted! This cannot be undone.") == false) {
        return false;
    }
}
