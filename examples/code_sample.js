// Sample JavaScript code with intentional issues to demonstrate Codiga analysis
// and opportunities for Tabnine suggestions

// Function with nested callbacks (demonstrates callback hell)
function fetchUserData(userId) {
  fetch('/api/users/' + userId) // String concatenation for URLs - potential security issue
    .then(function(response) {
      response.json().then(function(userData) {
        fetch('/api/posts?userId=' + userData.id) // Another string concatenation
          .then(function(response) {
            response.json().then(function(postsData) {
              // Deeply nested callbacks
              document.getElementById('results').innerHTML = postsData.map(post => 
                '<div>' + post.title + '</div>' // Potential XSS vulnerability with innerHTML
              ).join('');
            });
          });
      });
    });
}

// Inefficient array handling in loops
function processItems(items) {
  var results = [];
  for (var i = 0; i < items.length; i++) {
    // DOM query in a loop - performance issue
    var container = document.getElementsByClassName('item-container')[0];
    
    // Array concatenation in loop - performance issue
    results = results.concat([items[i].processed]);
    
    // Multiple calculations that could be cached
    var itemWidth = container.clientWidth / items.length;
    var itemHeight = container.clientHeight / items.length;
    
    // Redundant calculations
    renderItem(items[i], itemWidth, itemHeight);
  }
  return results;
}

// Using eval - security risk
function calculateValue(formula) {
  try {
    return eval(formula); // Security vulnerability - eval usage
  } catch (error) {
    console.error('Error calculating formula:', error);
    return 0;
  }
}

// Inconsistent string quotes
const config = {
  apiUrl: "https://api.example.com",
  timeout: 5000,
  retries: 3,
  'auth-token': 'abc123' // Inconsistent quote style
};

// Missing trailing commas in multiline object
const settings = {
  theme: 'dark',
  fontSize: 14,
  enableNotifications: true
}

// Function that could benefit from async/await refactoring
function loadUserProfile() {
  return new Promise((resolve, reject) => {
    setTimeout(() => {
      const userData = { name: 'John', role: 'Admin' };
      resolve(userData);
    }, 1000);
  });
}
