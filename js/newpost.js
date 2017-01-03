$(document).on("click", ".open-PreviewDialog", function () {
     var postContent = $("#content").val();
     var postTitle = $("#title").val();
     postContent = postContent.replace(/(?:\r\n|\r|\n)/g, "<br />");;

     $(".modal-body #post-content-prev").html( postContent );
     $(".modal-body #post-title-prev").html( postTitle );
});
