import { Redirect } from 'expo-router';
import { getSession } from '../services/session';

// Login is the landing page; users with a valid session skip straight to the dashboard.
export default function Index() {
    return <Redirect href={getSession() ? '/dashboard' : '/login'} />;
}
