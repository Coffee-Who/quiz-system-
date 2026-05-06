```javascript
const firebaseConfig = {
  apiKey: "AIzaSyBhgfPGUgGsWr4VmOUeaEe_cC0RNSx8I7U",
  authDomain: "swtc-portal-6930c.firebaseapp.com",
  projectId: "swtc-portal-6930c", // <--- 這裡要加逗點
  messagingSenderId: "447508396321",
  appId: "1:447508396321:web:ee8d1faaa0331590e5e660"
};

firebase.initializeApp(firebaseConfig);
const db = firebase.firestore();
