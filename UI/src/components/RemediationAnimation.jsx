import React, { useState, useEffect } from 'react';
import { Box, Heading, Text, Progress, VStack, SimpleGrid, Icon, useColorModeValue } from '@chakra-ui/react';
import { FiShield, FiTool, FiRefreshCw, FiCheck, FiCpu, FiAlertTriangle } from 'react-icons/fi';

// Steps to display while remediation is in progress
const steps = [
  { text: 'Analyzing vulnerabilities...', duration: 2200, icon: FiShield },
  { text: 'Applying security patches...', duration: 2800, icon: FiTool },
  { text: 'Updating device firmware...', duration: 3000, icon: FiCpu },
  { text: 'Hardening configurations...', duration: 2500, icon: FiAlertTriangle },
  { text: 'Verifying fixes...', duration: 2000, icon: FiRefreshCw },
  { text: 'Finalizing...', duration: 1500, icon: FiCheck }
];

export default function RemediationAnimation() {
  const [index, setIndex] = useState(0);
  const [progress, setProgress] = useState(0);

  useEffect(() => {
    let current = 0;
    const advance = () => {
      if (current < steps.length) {
        setIndex(current);
        setProgress(Math.round(((current + 1) / steps.length) * 100));
        const { duration } = steps[current];
        setTimeout(() => {
          current += 1;
          advance();
        }, duration);
      }
    };
    advance();
  }, []);

  const bg = useColorModeValue('rgba(255,255,255,0.8)', 'rgba(26,32,44,0.8)');
  const textColor = useColorModeValue('gray.800', 'gray.100');
  const accentColor = useColorModeValue('purple.500', 'purple.300');

  return (
    <Box
      position="fixed"
      inset={0}
      bg={bg}
      backdropFilter="blur(10px)"
      display="flex"
      alignItems="center"
      justifyContent="center"
      zIndex="modal"
      p={8}
    >
      <Box
        maxW="lg"
        w="full"
        p={10}
        borderRadius="2xl"
        bg="rgba(255,255,255,0.25)"
        borderWidth="1px"
        borderColor="rgba(255,255,255,0.4)"
        textAlign="center"
        boxShadow="xl"
      >
        <VStack spacing={8}>
          <Icon as={steps[index].icon} boxSize={14} color={accentColor} />
          <Heading size="md" color={textColor}>
            {steps[index].text}
          </Heading>
          <Progress w="full" value={progress} size="lg" colorScheme="purple" borderRadius="full" hasStripe isAnimated />
          <SimpleGrid columns={{ base: 2, md: 3 }} spacing={6} opacity={0.8}>
            {[FiShield, FiTool, FiRefreshCw, FiCpu, FiAlertTriangle, FiCheck].map((I, idx) => (
              <Icon key={idx} as={I} boxSize={8} color={accentColor} />
            ))}
          </SimpleGrid>
          <Text color={textColor}>{progress}% complete</Text>
        </VStack>
      </Box>
    </Box>
  );
}
