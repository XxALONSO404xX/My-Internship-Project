import React from 'react';
import { Box, Center, Spinner, VStack, Text, useColorModeValue } from '@chakra-ui/react';

// Full-screen overlay loader for scans
export default function FullScreenLoader({ isOpen, message }) {
  const bgColor = useColorModeValue('whiteAlpha.600', 'blackAlpha.600');
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
        <VStack spacing={4}>
          <Spinner size="xl" color="primary.500" />
          <Text color={useColorModeValue('black','white')} fontSize="lg">
            {message}
          </Text>
        </VStack>
      </Center>
    </Box>
  );
}
