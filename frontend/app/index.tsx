import { Redirect } from 'expo-router';

// Login is the landing page. Once sessions exist, redirect signed-in users to /home here.
export default function Index() {
    return <Redirect href="/login" />;
}
