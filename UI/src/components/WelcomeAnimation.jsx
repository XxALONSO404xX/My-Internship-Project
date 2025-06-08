import React, { useState, useEffect, useContext } from 'react';
import { VStack, Image, Heading, Text, Box, HStack, Progress, Spinner, Icon, useColorModeValue, SimpleGrid } from '@chakra-ui/react';
import { FiWifi, FiCheck, FiServer, FiShield, FiActivity } from 'react-icons/fi';
import { AuthContext } from '../contexts/AuthContext';

// Define startup statuses with icons and base durations
const statuses = [
  { text: 'Loading core modules...', duration: 800, icon: FiServer },
  { text: 'Establishing secure connection...', duration: 1200, icon: FiShield },
  { text: 'Scanning network infrastructure...', duration: 1500, icon: FiWifi },
  { text: 'Discovering IoT devices...', duration: 2000, icon: FiActivity },
  { text: 'Analyzing device capabilities...', duration: 1800, icon: FiActivity },
  { text: 'Finalizing setup...', duration: 1000, icon: FiCheck },
];

export default function WelcomeAnimation({ onComplete }) {
  // Access authenticated user
  const { user } = useContext(AuthContext);
  // Determine display name from user object
  const displayName = user?.name || user?.username || '';
  // Current entry holds text, icon, and duration
  const [entry, setEntry] = useState(statuses[0]);
  const [progress, setProgress] = useState(0);
  // Dynamic completion message
  const [statusMessage, setStatusMessage] = useState('');
  const dynamicMessages = [
    'Hang tight...',
    'Scanning network...',
    'Almost there...',
    'Loading modules...',
    'Connecting devices...'
  ];

  useEffect(() => {
    let currentIndex = 0;
    const update = () => {
      if (currentIndex < statuses.length) {
        const next = statuses[currentIndex];
        // Introduce random jitter +/-20%
        const delay = next.duration * (0.8 + Math.random() * 0.4);
        setEntry(next);
        setProgress(Math.round(((currentIndex + 1) / statuses.length) * 100));
        // update dynamic message each step
        setStatusMessage(dynamicMessages[currentIndex % dynamicMessages.length]);
        setTimeout(() => {
          currentIndex++;
          update();
        }, delay);
      } else {
        setEntry({ text: 'Setup complete!', duration: 0, icon: FiCheck });
        setProgress(100);
        // final message
        setStatusMessage('All done!');
        setTimeout(onComplete, 1000);
      }
    };
    update();
    return () => {};
  }, [onComplete]);

  const bg = useColorModeValue('rgba(255,255,255,0.7)', 'rgba(26,32,44,0.8)');
  const textColor = useColorModeValue('gray.800', 'white');
  const accentColor = useColorModeValue('blue.500', 'blue.300');

  return (
    <Box 
      position="fixed" 
      top={0} 
      left={0} 
      right={0} 
      bottom={0} 
      bg={bg}
      backdropFilter="blur(10px)"
      zIndex="modal"
      display="flex" 
      alignItems="center" 
      justifyContent="center"
      px={8}
    >
      <Box 
        maxW="2xl" 
        w="full"
        p={12}
        bg="rgba(255,255,255,0.2)"
        borderRadius="2xl"
        boxShadow="xl"
        borderWidth="1px"
        borderColor="rgba(255,255,255,0.3)"
        textAlign="center"
        position="relative"
        overflow="hidden"
        _before={{
          content: '""',
          position: 'absolute',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: 'linear-gradient(135deg, rgba(255,255,255,0.1) 0%, rgba(255,255,255,0) 100%)',
          zIndex: -1
        }}
      >
        {/* Hero Image with pulse animation */}
        <Box 
          as="img" 
          src="/internet-things_8002007.png" 
          alt="IoT Network" 
          w="280px" 
          h="280px"
          mx="auto"
          mb={10}
          objectFit="contain"
          borderRadius="xl"
          boxShadow="lg"
          p={6}
          bg="rgba(255,255,255,0.4)"
          animate={{ 
            scale: [1, 1.05, 1],
            opacity: [0.9, 1, 0.9]
          }}
          transition={{ 
            duration: 3,
            repeat: Infinity,
            ease: "easeInOut"
          }}
        />

        {/* Welcome Message */}
        <Box mb={12}>
          <Heading fontSize="3xl" fontWeight="bold" mb={4} color={textColor}>
            Welcome{displayName ? `, ${displayName}` : ''} to Your IoT Platform!
          </Heading>
          <Text fontSize="xl" mb={6} color={textColor}>
            Connecting your smart devices...
          </Text>
          
          <Progress 
            value={progress} 
            size="lg" 
            colorScheme="blue" 
            borderRadius="full" 
            mb={4}
            hasStripe
            isAnimated
          />
          <Text fontSize="md" color={accentColor}>
            {progress < 100 ? `${progress}% complete • ${statusMessage}` : 'All done!'}
          </Text>
        </Box>

        {/* Features Grid */}
        <SimpleGrid columns={{ base: 2, md: 4 }} spacing={6}>
          {[
            { icon: FiServer, text: 'Device Management' },
            { icon: FiWifi, text: 'Network Status' },
            { icon: FiShield, text: 'Security' },
            { icon: FiActivity, text: 'Analytics' }
          ].map((item, idx) => (
            <VStack 
              key={idx} 
              spacing={3} 
              p={6} 
              bg="rgba(255,255,255,0.2)"
              borderRadius="xl"
              borderWidth="1px"
              borderColor="rgba(255,255,255,0.3)"
              transition="all 0.2s"
              _hover={{
                transform: 'translateY(-2px)',
                boxShadow: 'lg',
                bg: 'rgba(255,255,255,0.3)'
              }}
            >
              <Icon as={item.icon} boxSize={8} color={accentColor} />
              <Text fontSize="md" fontWeight="medium" color={textColor}>{item.text}</Text>
            </VStack>
          ))}
        </SimpleGrid>
      </Box>
    </Box>
  );
}
