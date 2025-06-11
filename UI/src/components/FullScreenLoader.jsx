import React from 'react';
import { Box, Center, VStack, Text, useColorModeValue, Icon } from '@chakra-ui/react';
import { BsRadar } from 'react-icons/bs';
import { keyframes } from '@emotion/react';

// Full-screen overlay loader for scans
export default function FullScreenLoader({ isOpen, message }) {
  const bgColor = useColorModeValue('whiteAlpha.600', 'blackAlpha.600');
  
  // animated pulse ring
  const pulse = keyframes`
    0%   { transform: scale(0.6); opacity:0.8; }
    70%  { transform: scale(1.4); opacity:0; }
    100% { opacity:0; }
  `;

  const spin = keyframes`
    from { transform: rotate(0deg); }
    to   { transform: rotate(360deg); }
  `;

  if (!isOpen) return null;
  return (
    <Box
      position="fixed"
      top={0}
      left={0}
      width="100vw"
      height="100vh"
      bg={bgColor}
      backdropFilter="blur(4px)"
      zIndex="overlay"
    >
      <Center height="100%">
        <VStack spacing={6}>
          <Box position="relative" w="120px" h="120px">
            <Box position="absolute" inset="0" borderRadius="full" border="3px solid" borderColor="primary.400" animation={`${pulse} 1.5s ease-out infinite`} />
            <Box position="absolute" inset="0" borderRadius="full" border="3px solid" borderColor="primary.400" animation={`${pulse} 1.5s ease-out 0.75s infinite`} />
            <Icon as={BsRadar} boxSize={10} color="primary.500" position="absolute" top="50%" left="50%" transform="translate(-50%, -50%)" animation={`${spin} 2s linear infinite`} />
          </Box>
          <Text color={useColorModeValue('black','white')} fontSize="lg" textAlign="center">
            {message}
          </Text>
        </VStack>
      </Center>
    </Box>
  );
}
