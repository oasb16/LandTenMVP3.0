// Import the functions you need from the SDKs you need
import { initializeApp } from "firebase/app";
import { getAnalytics } from "firebase/analytics";
// TODO: Add SDKs for Firebase products that you want to use
// https://firebase.google.com/docs/web/setup#available-libraries

// Your web app's Firebase configuration
const firebaseConfig = {
  apiKey: "AIzaSyB5GWJtxkxZjf0oND3pZtxg6btH3Jzn3dA",
  authDomain: "landtenmvp30.firebaseapp.com",
  projectId: "landtenmvp30",
  storageBucket: "landtenmvp30.firebasestorage.app",
  messagingSenderId: "824624615863",
  appId: "1:824624615863:web:f81a8a641c0e75db4e9832",
  measurementId: "G-V01QCB1PM0"
};

// Initialize Firebase
const app = initializeApp(firebaseConfig);
const analytics = getAnalytics(app);

export { app, analytics };
