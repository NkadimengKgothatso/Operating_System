#include<stdio.h>
#include<string.h>


int main(int argc, char * argv[])
{
    if (argc < 2) {
        printf("Usage: %s <string>\n", argv[0]);
        return 1;
    }

    char *input = argv[1];
    size_t len = strlen(input);
    
    for (int i = len - 1; i >= 0; i--) {
        putchar(input[i]);
    }
    putchar('\n');

    return 0;
}