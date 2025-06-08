import React, { useEffect } from 'react';
import { Box } from '@chakra-ui/react';
import { useInView } from 'react-intersection-observer';

export const InfiniteScroll = ({ 
  children, 
  loadMore, 
  hasMore, 
  loader,
  threshold = 0.8,
  debounce = 200
}) => {
  const [ref, inView] = useInView({
    threshold,
    triggerOnce: false,
  });

  useEffect(() => {
    let timer;
    if (inView && hasMore) {
      timer = setTimeout(() => {
        loadMore();
      }, debounce);
    }
    return () => clearTimeout(timer);
  }, [inView, hasMore, loadMore, debounce]);

  return (
    <Box>
      {children}
      <Box ref={ref} pt={4}>
        {hasMore && loader}
      </Box>
    </Box>
  );
};
