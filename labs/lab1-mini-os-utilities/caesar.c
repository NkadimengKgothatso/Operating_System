#include<stdio.h>
#include<string.h>
#include<stdlib.h>
#include<ctype.h>

int main(int argc, char *argv[]) {
    if (argc != 3) {
        printf("Usage: ./caesar <shift> <text>\n");
        return 1;
    }

    char *input = argv[2];
    int shift = atoi(argv[1]);
    shift = ((shift % 26) + 26) % 26;

    
        for (int i = 0; argv[2][i] != '\0'; i++) {
            char c = argv[2][i];
            if (isupper(c))
                putchar(((c - 'A' + shift) % 26) + 'A');
            else if (islower(c))
                putchar(((c - 'a' + shift) % 26) + 'a');
            else
                putchar(c);
        }
        putchar('\n');
    return 0;
}