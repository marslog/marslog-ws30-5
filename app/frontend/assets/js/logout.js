function logoutConfirm() {
  Swal.fire({
    title: 'Are you sure?',
    text: 'You will be logged out of the system.',
    icon: 'warning',
    showCancelButton: true,
    confirmButtonColor: '#e53e3e',
    cancelButtonColor: '#718096',
    confirmButtonText: 'Logout',
    background: '#1e1f36',
    color: '#fff'
  }).then((result) => {
    if (result.isConfirmed) {
      window.location.href = '/login/logout.php';
    }
  });
}

