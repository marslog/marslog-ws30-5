function logoutConfirm() {
  Swal.fire({
    title: 'Are you sure?',
    text: 'You will be logged out of the system.',
    icon: 'warning',
    showCancelButton: true,
    confirmButtonColor: '#e53e3e',
    cancelButtonColor: '#718096',
    confirmButtonText: 'Logout',
    customClass: {
        popup: 'swal2-popup',
        title: 'swal2-title',
        htmlContainer: 'swal2-html-container',
        confirmButton: 'swal2-confirm',
        cancelButton: 'swal2-cancel'
    }
  }).then((result) => {
    if (result.isConfirmed) {
      window.location.href = '/login/logout.php';
    }
  });
}

const ctxBar = document.getElementById('syslogTrendChart').getContext('2d');
new Chart(ctxBar, {
  type: 'bar',
  data: {
    labels: ['00h', '04h', '08h', '12h', '16h', '20h'],
    datasets: [{
      label: 'Syslog Events',
      data: [1200, 2300, 1800, 2400, 3100, 3500],
      backgroundColor: 'var(--color-purple-gradient-end)'
    }]
  },
  options: { responsive: true, maintainAspectRatio: false,
    scales: {
        x: {
            ticks: { color: 'var(--color-chart-label)' },
            grid: { color: 'var(--color-chart-grid)' }
        },
        y: {
            ticks: { color: 'var(--color-chart-label)' },
            grid: { color: 'var(--color-chart-grid)' }
        }
    },
    plugins: { legend: { labels: { color: 'var(--color-text-primary)' } } }
  }
});

const ctxPie = document.getElementById('logSourcePie').getContext('2d');
new Chart(ctxPie, {
  type: 'pie',
  data: {
    labels: ['Firewall', 'Web Server', 'Database', 'Application'],
    datasets: [{
      label: 'Log Sources',
      data: [12340, 9820, 7650, 5230],
      backgroundColor: ['#f87171', '#60a5fa', '#34d399', '#fbbf24']
    }]
  },
  options: { responsive: true, maintainAspectRatio: false,
    plugins: { legend: { labels: { color: 'var(--color-text-primary)' } } }
  }
});