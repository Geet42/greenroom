import Navbar from "../components/Navbar";
import Footer from "../components/Footer";
import AuthForm from "../components/AuthForm";

export default function Login() {
  return (
    <div className="flex min-h-screen flex-col">
      <Navbar />
      <main className="flex-1">
        <AuthForm mode="login" />
      </main>
      <Footer />
    </div>
  );
}
