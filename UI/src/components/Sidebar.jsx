import React, { useState, useContext } from 'react';
import { NavLink, useLocation, useNavigate } from 'react-router-dom';
import {
  Box,
  Flex,
  Text,
  Icon,
  VStack,
  HStack,
  IconButton,
  useColorModeValue,
  Collapse,
  Button,
  Tooltip,
  useBreakpointValue,
  AlertDialog,
  AlertDialogOverlay,
  AlertDialogContent,
  AlertDialogHeader,
  AlertDialogBody,
  AlertDialogFooter,
  useDisclosure,
} from '@chakra-ui/react';
import {
  FiHome,
  FiCpu,
  FiShield,
  FiActivity,
  FiSettings,
  FiChevronDown,
  FiChevronRight,
  FiMenu,
  FiX,
  FiPower,
  FiWifi,
  FiCommand,
} from 'react-icons/fi';
import { AuthContext } from '../contexts/AuthContext';

// Navigation item component
const NavItem = ({
  icon: IconComp,
  label,
  to,
  subItems = [],
  isExpanded = true,
  onItemClick,
}) => {
  const { pathname } = useLocation();
  const [isOpen, setIsOpen] = useState(false);
  const hasSubItems = subItems.length > 0;
  
  const isActive = pathname === to || 
    (hasSubItems && subItems.some(item => pathname.startsWith(item.to)));
  
  const activeBg = useColorModeValue('primary.50', 'primary.900');
  const hoverBg = useColorModeValue('gray.50', 'gray.700');
  const activeColor = useColorModeValue('primary.600', 'primary.300');
  const textColor = useColorModeValue('gray.700', 'gray.200');
  const borderColor = useColorModeValue('gray.200', 'gray.600');

  const handleClick = (e) => {
    if (hasSubItems) {
      e.preventDefault();
      setIsOpen(!isOpen);
    }
    if (onItemClick) onItemClick();
  };

  return (
    <Box as="li" listStyleType="none">
      <NavLink
        to={hasSubItems ? '#' : to}
        style={{ textDecoration: 'none' }}
        onClick={handleClick}
      >
        <Flex
          align="center"
          px={4}
          py={4}
          mx={2}
          my={1}
          borderRadius="lg"
          bg={isActive ? activeBg : 'transparent'}
          color={isActive ? activeColor : textColor}
          _hover={{
            bg: isActive ? activeBg : hoverBg,
            textDecoration: 'none',
          }}
          transition="all 0.2s"
          minH="50px"
        >
          {IconComp && (
            <Icon as={IconComp} mr={isExpanded ? 4 : 0} boxSize={6} />
          )}
          
          {isExpanded && (
            <>
              <Text fontSize="md" fontWeight={isActive ? 'semibold' : 'normal'} flex={1}>
                {label}
              </Text>
              {hasSubItems && (
                <Icon
                  as={isOpen ? FiChevronDown : FiChevronRight}
                  ml="auto"
                  transition="transform 0.2s"
                  transform={isOpen ? 'rotate(180deg)' : 'none'}
                  boxSize={5}
                />
              )}
            </>
          )}
        </Flex>
      </NavLink>

      {hasSubItems && isExpanded && (
        <Collapse in={isOpen} animateOpacity>
          <Box as="ul" pl={6} mt={1} borderLeftWidth="1px" borderLeftColor={borderColor} listStyleType="none" m={0} p={0}>
            {subItems.map((item) => (
              <NavItem
                key={item.to}
                icon={item.icon}
                label={item.name}
                to={item.to}
                isExpanded={isExpanded}
                onItemClick={onItemClick}
              />
            ))}
          </Box>
        </Collapse>
      )}
    </Box>
  );
};

// Sidebar component
const Sidebar = ({ isOpen, onClose }) => {
  const { user, logout } = useContext(AuthContext);
  const [isExpanded, setIsExpanded] = useState(true);
  const navigate = useNavigate();
  const isMobile = useBreakpointValue({ base: true, md: false });
  
  // Navigation links
  const navItems = [
    { name: 'Dashboard', icon: FiHome,     to: '/',           roles: ['admin','user'] },
    { name: 'Devices',   icon: FiCpu,      to: '/devices',     roles: ['admin','user'] },
    { name: 'Activity',  icon: FiActivity, to: '/activities',  roles: ['admin','user'],
      subItems: [
        { name: 'Logs',   to: '/activities/logs'   },
        { name: 'Alerts', to: '/activities/alerts' }
      ]
    },
    { name: 'Security', icon: FiShield,   to: '/security',    roles: ['admin','user'] },
    { name: 'Network',  icon: FiWifi,     to: '/network',     roles: ['admin','user'] },
    { name: 'Rules',    icon: FiCommand,  to: '/rules',       roles: ['admin','user'] }
  ];

  // Filter navigation items based on user role
  const filteredNavItems = navItems.filter(item => 
    item.roles.includes(user?.role || 'user')
  );

  const { isOpen: isLogoutOpen, onOpen: onLogoutOpen, onClose: onLogoutClose } = useDisclosure();
  const cancelRef = React.useRef();

  const handleLogout = () => {
    onLogoutClose();
    logout();
    navigate('/login');
  };

  const toggleSidebar = () => {
    if (isMobile) {
      onClose?.();
    } else {
      setIsExpanded(!isExpanded);
    }
  };

  const bgColor = useColorModeValue('white', 'gray.800');
  const borderColor = useColorModeValue('gray.200', 'gray.700');
  const textColor = useColorModeValue('gray.800', 'white');

  return (
    <>
      <Box
        as="aside"
        display="flex"
        flexDirection="column"
        bg={bgColor}
        borderRightWidth="1px"
        borderRightColor={borderColor}
        w={{ base: '100%', md: isExpanded ? '280px' : '80px' }}
        h="100vh"
        pos="fixed"
        top="0"
        left="0"
        zIndex="sticky"
        transition="all 0.3s ease"
        transform={{
          base: isOpen ? 'translateX(0)' : 'translateX(-100%)',
          md: 'translateX(0)'
        }}
      >
      {/* Header */}
      <Flex
        h="16"
        align="center"
        justify="space-between"
        px={4}
        borderBottomWidth="1px"
        borderBottomColor={borderColor}
      >
        {isExpanded && (
          <Text fontSize="xl" fontWeight="bold" color={textColor}>
            IoT Platform
          </Text>
        )}
        
        <IconButton
          icon={isMobile ? <FiX /> : <FiMenu />}
          variant="ghost"
          onClick={toggleSidebar}
          aria-label={isExpanded ? 'Collapse sidebar' : 'Expand sidebar'}
        />
      </Flex>

      {/* Navigation */}
      <Box
        as="nav"
        flex="1"
        overflowY="auto"
        py={4}
        px={4}
        css={{
          '&::-webkit-scrollbar': {
            width: '4px',
          },
          '&::-webkit-scrollbar-track': {
            background: 'transparent',
          },
          '&::-webkit-scrollbar-thumb': {
            background: borderColor,
            borderRadius: '4px',
          },
        }}
      >
        <VStack as="ul" spacing={1} align="stretch" px={2}>
          {filteredNavItems.map((item) => (
            <NavItem
              key={item.to}
              icon={item.icon}
              label={item.name}
              to={item.to}
              subItems={item.subItems}
              isExpanded={isExpanded}
              onItemClick={isMobile ? onClose : undefined}
            />
          ))}
        </VStack>
      </Box>

      {/* Footer */}
      <Box
        p={4}
        borderTopWidth="1px"
        borderTopColor={borderColor}
      >
        {isExpanded ? (
          <VStack spacing={2} align="stretch">
            {user?.name && (
              <Text fontSize="sm" fontWeight="medium" color={textColor} isTruncated>
                {user.name}
              </Text>
            )}
            <Button
              leftIcon={<FiPower />}
              variant="ghost"
              justifyContent="flex-start"
              colorScheme="red"
              size="md"
              height="48px"
              onClick={(e) => {
                e.preventDefault();
                onLogoutOpen();
              }}
            >
              Logout
            </Button>
          </VStack>
        ) : (
          <Flex justify="center">
            <Tooltip label="Logout" placement="right">
              <IconButton
                icon={<FiPower />}
                aria-label="Logout"
                variant="ghost"
                colorScheme="red"
                size="lg"
                boxSize="48px"
                onClick={(e) => {
                  e.preventDefault();
                  onLogoutOpen();
                }}
              />
            </Tooltip>
          </Flex>
        )}
      </Box>
      </Box>

      {/* Logout Confirmation Dialog */}
      <AlertDialog
        isOpen={isLogoutOpen}
        leastDestructiveRef={cancelRef}
        onClose={onLogoutClose}
        isCentered
      >
        <AlertDialogOverlay bg="blackAlpha.600" backdropFilter="blur(4px)">
          <AlertDialogContent mx={4}>
            <AlertDialogHeader fontSize="lg" fontWeight="bold">
              Confirm Logout
            </AlertDialogHeader>

            <AlertDialogBody>
              Are you sure you want to log out? You'll need to sign in again to access your account.
            </AlertDialogBody>

            <AlertDialogFooter>
              <Button ref={cancelRef} onClick={onLogoutClose}>
                Cancel
              </Button>
              <Button colorScheme="red" onClick={handleLogout} ml={3}>
                Logout
              </Button>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialogOverlay>
      </AlertDialog>
    </>
  );
};

export default Sidebar;
