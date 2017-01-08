/**
* @description Populates the modal-body inputs with values from post
*/
$(document).on('click', '.open-PreviewDialog', function () {
     var postContent = $('#content').val();
     var postTitle = $('#title').val();
     postContent = postContent.replace(/(?:\r\n|\r|\n)/g, '<br />');;

     $('.modal-body #post-content-prev').html( postContent );
     $('.modal-body #post-title-prev').html( postTitle );
});

/**
* @description Comfirms the deletion of an item.
* @returns {boolean} false if user didn't click OK in confirm box
*/
function confirmDelete() {
    if (confirm('This item will be deleted! This cannot be undone.') == false) {
        return false;
    }
}

/**
* @description Used to allow users to edit comments on posts. Transforms td cell into editable field, then submits new comment
* @param {Number} comment ID to edit and submit. Used as key
* @returns {boolean} used to submit or prevent submission
*/
function editComment(commentId) {
  if ($('#' + commentId + '_edit_btn').html().trim() == 'Edit') {
      // User wants to edit the comment content.  Make editable based on ID
      $('#' + commentId + '_comment_content').prop('contenteditable', true);
      $('#' + commentId + '_comment_content').focus();
      event.preventDefault();   // Prevent form submission
  } else {
      // User edited and clicked 'Save'. Disable editing
      $('#' + commentId + '_comment_content').prop('contenteditable', false);
      // Find specific form for individual comment
      var currForm = $('#' + $('#' + commentId + '_edit_btn').val()+'_form');
      // Create hidden input based on edited comment content.
      var input = $('<input>').attr('type', 'hidden').attr('name', $('#' + commentId + '_edit_btn').val()).val($('#' + commentId + '_comment_content').html());
      currForm.append($(input));  // Add hidden input. Editable field isn't in POST
      return true;
  }
  // Change Edit button to say Save
  $('#' + commentId + '_edit_btn').html($('#' + commentId + '_edit_btn').html().trim() == 'Edit' ? 'Save' : 'Edit');
}
