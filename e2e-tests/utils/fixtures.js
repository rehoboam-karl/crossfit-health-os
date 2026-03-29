/**
 * Test Fixtures - Sample data for tests
 */

const TEST_USERS = {
  valid: {
    email: 'testuser@example.com',
    password: 'SecurePass123',
    name: 'Test Athlete',
    birthDate: '1990-05-15',
    weightKg: 75.0,
    heightCm: 175,
    fitnessLevel: 'intermediate',
    goals: ['strength', 'conditioning']
  },
  
  weakPassword: {
    email: 'weak@example.com',
    password: 'weakpass',
    name: 'Weak Password User'
  },
  
  noUppercase: {
    email: 'noupper@example.com',
    password: 'securepass123',
    name: 'No Uppercase User'
  },
  
  noNumber: {
    email: 'nonumber@example.com',
    password: 'SecurePassword',
    name: 'No Number User'
  },
  
  duplicate: {
    email: 'duplicate@example.com',
    password: 'SecurePass123',
    name: 'Duplicate User'
  },
  
  existing: {
    email: 'existing@example.com',
    password: 'ExistingPass123',
    name: 'Existing User'
  }
};

const REGISTRATION_DATA = {
  valid: {
    email: 'newuser@example.com',
    password: 'SecurePass123',
    confirmPassword: 'SecurePass123',
    name: 'New Athlete',
    birthDate: '1995-03-10',
    weightKg: '80',
    heightCm: '180',
    fitnessLevel: 'beginner',
    goals: ['strength']
  },
  
  validMinimal: {
    email: 'minimal@example.com',
    password: 'SecurePass123',
    confirmPassword: 'SecurePass123',
    name: 'Minimal User'
  },
  
  passwordMismatch: {
    email: 'mismatch@example.com',
    password: 'SecurePass123',
    confirmPassword: 'DifferentPass456',
    name: 'Mismatch User'
  },
  
  shortPassword: {
    email: 'short@example.com',
    password: 'Ab1',
    confirmPassword: 'Ab1',
    name: 'Short Password User'
  },
  
  invalidEmail: {
    email: 'notanemail',
    password: 'SecurePass123',
    confirmPassword: 'SecurePass123',
    name: 'Invalid Email User'
  },
  
  duplicateEmail: {
    email: 'taken@example.com',
    password: 'SecurePass123',
    confirmPassword: 'SecurePass123',
    name: 'Taken Email User'
  }
};

const ONBOARDING_DATA = {
  full: {
    name: 'Onboarded User',
    appFocus: 'full',
    primaryGoal: 'both',
    fitnessLevel: 'intermediate',
    availableDays: ['monday', 'wednesday', 'friday'],
    preferredTime: 'morning',
    methodologies: ['hwpo']
  },
  
  trainingOnly: {
    name: 'Training Only User',
    appFocus: 'training',
    primaryGoal: 'strength',
    fitnessLevel: 'advanced',
    availableDays: ['tuesday', 'thursday', 'saturday'],
    preferredTime: 'evening',
    methodologies: ['hwpo']
  },
  
  customDiet: {
    name: 'Custom Diet User',
    appFocus: 'custom',
    primaryGoal: 'health',
    fitnessLevel: 'beginner',
    availableDays: ['monday', 'tuesday', 'wednesday', 'thursday', 'friday'],
    preferredTime: 'afternoon',
    methodologies: ['custom']
  },
  
  athlete: {
    name: 'Athlete User',
    appFocus: 'full',
    primaryGoal: 'conditioning',
    fitnessLevel: 'athlete',
    availableDays: ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday'],
    preferredTime: 'morning',
    methodologies: ['competitor_wod']
  }
};

const FORM_VALIDATION = {
  invalidEmails: [
    'notanemail',
    '@example.com',
    'user@',
    'user name@example.com',
    'user@ example.com',
    ''
  ],
  
  weakPasswords: [
    'short',
    'alllowercase1',
    'ALLUPPERCASE1',
    'NoNumbers',
    'NoUppercase1',
    '12345678'
  ],
  
  futureBirthDate: (() => {
    const future = new Date();
    future.setFullYear(future.getFullYear() + 1);
    return future.toISOString().split('T')[0];
  })()
};

module.exports = {
  TEST_USERS,
  REGISTRATION_DATA,
  ONBOARDING_DATA,
  FORM_VALIDATION
};
